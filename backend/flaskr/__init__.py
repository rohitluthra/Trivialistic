import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

#----------------------------------------------------------------------------#
# App Setup
#----------------------------------------------------------------------------#

def create_app(test_config=None):
  '''create and configure the app'''
  app = Flask(__name__)
  setup_db(app)

  '''
  DONE: Set up CORS. Allow '*' for origins. Delete the sample route after completing the TODOs
  '''
  # CORS(app)
  cors = CORS(app, resources={r"/api/*": {"origins": "*"}})


  '''
  DONE: Use the after_request decorator to set Access-Control-Allow
  '''
  # CORS Headers
  @app.after_request
  def after_request(response):
      response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,true')
      response.headers.add('Access-Control-Allow-Methods', 'GET,PATCH,POST,DELETE,OPTIONS')
      return response

#----------------------------------------------------------------------------#
# Custom Functions
#----------------------------------------------------------------------------#

  def paginate_questions(request, selection):
    '''Paginates and formats questions

    Parameters:
      * <HTTP object> request, that may contain a "page" value
      * <database selection> selection of questions, queried from database

    Returns:
      * <list> list of dictionaries of questions, max. 10 questions

    '''
    # Get page from request. If not given, default to 1
    page = request.args.get('page', 1, type=int)

    # Calculate start and end slicing
    start =  (page - 1) * QUESTIONS_PER_PAGE
    end = start + QUESTIONS_PER_PAGE

    # Format selection into list of dicts and slice
    questions = [question.format() for question in selection]
    current_questions = questions[start:end]

    return current_questions

  def getErrorMessage(error, default_text):
    '''Returns default error text or custom error message (if not applicable)

    Parameters:
      * <error> system generated error message which contains a description message
      * <string> default text to be used as error message if Error has no specific message

    Returns:
      * <string> specific error message or default text(if no specific message is given)

    '''
    try:
      # Return message contained in error, if possible
      return error.description["message"]
    except TypeError:
      # otherwise, return given default text
      return default_text


#  API Endpoints
#  ----------------------------------------------------------------
#  NOTE:  For explanation of each endpoint, please have look at the backend/README.md file.
#         DOC Strings only contain short description and list of test classes

#----------------------------------------------------------------------------#
# Endpoint /questions GET/POST/DELETE
#----------------------------------------------------------------------------#
  '''
  # DONE Create an endpoint to handle GET requests for questions including pagination (every 10 questions).
  This endpoint should return a list of questions, number of total questions, current category, categories.
  '''
  @app.route('/questions', methods=['GET'])
  def get_questions():
    # Returns paginated questions
    selection = Question.query.order_by(Question.id).all()
    questions_paginated = paginate_questions(request, selection)
    if len(questions_paginated) == 0:
      abort(404)

    categories = Category.query.all()
    categories_all = [category.format() for category in categories]

    categories_returned = []
    for cat in categories_all:
      categories_returned.append(cat['type'])

    return jsonify({
      'success': True,
      'questions': questions_paginated,
      'total_questions': len(selection),
      'categories' : categories_returned,
      'current_category' : categories_returned
      })

#       app = Flask(__name__)
#       @app.route ('/questions/ <int: questions_id>', methods = ["GET"])
#       def get_questions(questions_id):
#         ordered = db.query.order_by(db.id).all()
#         try:
#             return jsonify({
#             'success': True
#             'questionsOrder': ordered
#             })
#         except:
#             abort(422)

  '''
  Create an endpoint to DELETE question using a question ID.
  '''
  @app.route('/questions/<int:question_id>', methods=['DELETE'])
  def delete_questions(question_id):

    question = Question.query.filter(Question.id == question_id).one_or_none()
    if not question:
      abort(400, {'message': 'Question does not exist.'})
    try:
      question.delete()
      return jsonify({
        'success': True,
        'deleted': question_id
      })
    except:
      abort(400)

  '''
  # Create an endpoint to POST a new question, which will require the question and answer text, category, and difficulty score.
  '''
  @app.route('/questions', methods=['POST'])
  def create_or_search_questions():

    body = request.get_json()

    if not body:
      abort(400, {'message': 'request does not contain a valid JSON body.'})

    search_term = body.get('searchTerm', None)

    if search_term:
      questions = Question.query.filter(Question.question.contains(search_term)).all()
      if not questions:
        abort(404, {'message': 'no questions that contains "{}" found.'.format(search_term)})

      questions_found = [question.format() for question in questions]
      selections = Question.query.order_by(Question.id).all()

      categories = Category.query.all()
      categories_all = [category.format() for category in categories]

      return jsonify({
        'success': True,
        'questions': questions_found,
        'total_questions': len(selections),
        'current_category' : categories_all
      })

    # new question case
    new_question = body.get('question', None)
    new_answer = body.get('answer', None)
    new_category = body.get('category', None)
    new_difficulty = body.get('difficulty', None)

    if not new_question or not new_answer or  not new_category or not new_difficulty:
      abort(400, {'message': 'Please fill all the items'})


    try:
      # Try to insert a new question. If anything went wrong, raise 422 "unprocessable"
      question = Question(
        question = new_question,
        answer = new_answer,
        category= new_category,
        difficulty = new_difficulty
        )
      question.insert()

      selections = Question.query.order_by(Question.id).all()
      questions_paginated = paginate_questions(request, selections)

      return jsonify({
        'success': True,
        'created': question.id,
        'questions': questions_paginated,
        'total_questions': len(selections)
      })

    except:
      abort(422)

#----------------------------------------------------------------------------#
# Endpoint /quizzes POST
#----------------------------------------------------------------------------#
  '''
  DONE: Create a POST endpoint to get questions to play the quiz.
  This endpoint should take category and previous question parameters
  and return a random questions within the given category,
  if provided, and that is not one of the previous questions.

  TEST: In the "Play" tab, after a user selects "All" or a category,
  one question at a time is displayed, the user is allowed to answer
  and shown whether they were correct or not.
  '''
  @app.route('/quizzes', methods=['POST'])
  def play_quiz():

    body = request.get_json()

    if not body:
      # If no JSON Body was given, raise error.
      abort(400, {'message': 'Please provide a JSON body with previous question Ids and optional category.'})

    # Get paramters from JSON Body.
    previous_questions = body.get('previous_questions', None)
    current_category = body.get('quiz_category', None)

    if not previous_questions:
      if current_category:
        # if no list with previous questions is given, but a category , just gut any question from this category.
        questions_raw = (Question.query
          .filter(Question.category == str(current_category['id']))
          .all())
      else:
        # if no list with previous questions is given and also no category , just gut any question.
        questions_raw = (Question.query.all())
    else:
      if current_category:
      # if a list with previous questions is given and also a category, query for questions which are not contained in previous question and are in given category
        questions_raw = (Question.query
          .filter(Question.category == str(current_category['id']))
          .filter(Question.id.notin_(previous_questions))
          .all())
      else:
        # # if a list with previous questions is given but no category, query for questions which are not contained in previous question.
        questions_raw = (Question.query
          .filter(Question.id.notin_(previous_questions))
          .all())

    # Format questions & get a random question
    questions_formatted = [question.format() for question in questions_raw]
    random_question = questions_formatted[random.randint(0, len(questions_formatted))]

    return jsonify({
        'success': True,
        'question': random_question
      })
#----------------------------------------------------------------------------#
# Endpoint /catogories GET/POST/DELETE
#----------------------------------------------------------------------------#

  #DONE Create an endpoint to handle GET requests for all available categories.
  @app.route('/categories', methods=['GET'])
  def get_categories():

    categories = Category.query.all()
    if not categories:
      abort(404)

    categories_all = [category.format() for category in categories]

    categories_returned = []
    for cat in categories_all:
      categories_returned.append(cat['type'])

    return jsonify({
      'success': True,
      'categories' : categories_returned
    })

  # DONE: Create a GET endpoint to get questions based on category.
  @app.route('/categories/<string:category_id>/questions', methods=['GET'])
  def get_questions_from_categories(category_id):


    # Query for all Questions that match category id
    selection = (Question.query.filter(Question.category == str(category_id)).order_by(Question.id).all())

    if not selection:
      abort(400, {'message': 'No questions with category {} found.'.format(category_id) })

    questions_paginated = paginate_questions(request, selection)

    if not questions_paginated:
      abort(404, {'message': 'No questions in selected page.'})

    return jsonify({
      'success': True,
      'questions': questions_paginated,
      'total_questions': len(selection),
      'current_category' : category_id
      })





#----------------------------------------------------------------------------#
# BONUS: API to create/delete new/old Categories
#----------------------------------------------------------------------------#

  @app.route('/categories', methods=['POST'])
  def create_categories():
    """Creates a new category

      Tested by:
        Success:
          - test_create_category
        Error:
          - test_error_400_create_category_missing_json

    """
    body = request.get_json()

    # If request does not contain valid JSON, raise 400.
    if not body:
      abort(400, {'message': 'request does not contain a valid JSON body.'})

    # Get field informations from request body
    new_type = body.get('type', None)

    # Make sure that all required fields are given.
    # Otherwise, respond with error message that describes what is missing
    if not new_type:
      abort(400, {'message': 'no type for new category provided.'})

    try:
      # Try to insert a new category. If anything went wrong, raise 422 "unprocessable"
      category = Category(type = new_type)
      category.insert()

      # After succesfully insertion, get all categories
      selections = Category.query.order_by(Category.id).all()
      categories_all = [category.format() for category in selections]

      # Return succesfull response
      return jsonify({
        'success': True,
        'created': category.id,
        'categories': categories_all,
        'total_categories': len(selections)
      })

    except:
      abort(422)

  @app.route('/categories/<int:category_id>', methods=['DELETE'])
  def delete_categories(category_id):
    """Delete a category

      Tested by:
        Success:
          - test_delete_category
        Error:
          - test_404_delete_category

    """
    category = Category.query.filter(Category.id == category_id).one_or_none()
    if not category:
      abort(400, {'message': 'Category with id {} does not exist.'.format(category_id)})
    try:
      category.delete()
      return jsonify({
        'success': True,
        'deleted': category_id
      })

    except:
      abort(422)

#----------------------------------------------------------------------------#
# API error handler & formatter.
#----------------------------------------------------------------------------#

  # DONE: Create error handlers for all expected errors

  @app.errorhandler(400)
  def bad_request(error):
    return jsonify({
      "success": False,
      "error": 400,
      "message": getErrorMessage(error, "bad request")
      }), 400

  @app.errorhandler(404)
  def ressource_not_found(error):
    return jsonify({
      "success": False,
      "error": 404,
      "message": getErrorMessage(error, "resource not found")
      }), 404

  @app.errorhandler(405)
  def method_not_allowed(error):
    return jsonify({
      "success": False,
      "error": 405,
      "message": "method not allowed"
      }), 405

  @app.errorhandler(422)
  def unprocessable(error):
    return jsonify({
      "success": False,
      "error": 422,
      "message": getErrorMessage(error, "unprocessable")
      }), 422

  @app.errorhandler(500)
  def internal_server_error(error):
    return jsonify({
      "success": False,
      "error": 500,
      "message": "internal server error"
      }), 500

  return app

    