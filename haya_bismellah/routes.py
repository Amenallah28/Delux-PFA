import requests
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from .models import Review
from .forms import ReviewForm
from .models import db, Review 

routes = Blueprint('routes', __name__)

@routes.route('/')
@login_required 
def home():
    return render_template("home.html", user=current_user, year=datetime.now().year)

""" OpenCage API key"""
opencage_api_key = '1e26944be7134917a051751f5c260a48'

""" Yelp API key """
yelp_api_key = 'sdcMabW8XLnBAXxP3NTEWUASNEuxpioz-qg0s6iSXn9MIilzMYS-fkMN5pVrgFhCfGK6suC1JWEAaWc6ZpVK80NRJqSEFM-zqGhshn89Q-HTVw6TY36DlN-znKyTZnYx'


@routes.route('/restaurant/<restaurant_id>', methods=['GET', 'POST'])
@login_required
def restaurant_details(restaurant_id):
    """ Get restaurant details using Yelp API """
    details_url = f'https://api.yelp.com/v3/businesses/{restaurant_id}'
    headers = {
        'Authorization': f'Bearer {yelp_api_key}'
    }
    response = requests.get(details_url, headers=headers)
    restaurant_details = response.json()

    if 'error' in restaurant_details:
        flash('Could not fetch restaurant details', category='error')
        return redirect(url_for('routes.home'))

    # Handle review submission
    form = ReviewForm()
    if form.validate_on_submit():
        new_review = Review(
            user_id=current_user.id,
            restaurant_id=restaurant_id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(new_review)
        db.session.commit()
        flash('Review added successfully!', category='success')
        return redirect(url_for('routes.restaurant_details', restaurant_id=restaurant_id))

    reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()

    return render_template('restaurant_details.html', restaurant=restaurant_details, form=form, reviews=reviews)

@routes.route('/search_location', methods=['GET'])
@login_required
def search_location():
    location = request.args.get('location')
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit

    if not location:
        flash('Location is required', category='error')
        return redirect(url_for('routes.home'))

    """ Get coordinates using OpenCage API """
    geocode_url = f'https://api.opencagedata.com/geocode/v1/json?q={location}&key={opencage_api_key}'
    response = requests.get(geocode_url)
    data = response.json()

    if not data['results']:
        flash('Could not find location', category='error')
        return redirect(url_for('routes.home'))

    latitude = data['results'][0]['geometry']['lat']
    longitude = data['results'][0]['geometry']['lng']

    """ Get top-rated restaurants using Yelp API """
    search_url = f'https://api.yelp.com/v3/businesses/search?latitude={latitude}&longitude={longitude}&categories=restaurants&sort_by=rating&limit={limit}&offset={offset}'
    headers = {
        'Authorization': f'Bearer {yelp_api_key}'
    }
    response = requests.get(search_url, headers=headers)
    top_rated_restaurants = response.json()

    if not top_rated_restaurants.get('businesses'):
        return render_template('no_restaurants.html', location=location)

    return render_template('top_rated_restaurants.html', 
                           top_rated_restaurants=top_rated_restaurants['businesses'], 
                           latitude=latitude, longitude=longitude, 
                           location=location, page=page)



@routes.route('/search_cuisine', methods=['GET'])
@login_required
def search_cuisine():
    latitude = request.args.get('latitude')
    longitude = request.args.get('longitude')
    cuisine = request.args.get('cuisine')
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit

    if not latitude or not longitude or not cuisine:
        flash('Latitude, longitude, and cuisine are required', category='error')
        return redirect(url_for('routes.home'))

    """ Get restaurants by cuisine using Yelp API """
    search_url = f'https://api.yelp.com/v3/businesses/search?latitude={latitude}&longitude={longitude}&categories={cuisine}&limit={limit}&offset={offset}'
    headers = {
        'Authorization': f'Bearer {yelp_api_key}'
    }
    response = requests.get(search_url, headers=headers)
    restaurants_by_cuisine = response.json()

    if not restaurants_by_cuisine.get('businesses'):
        return render_template('no_restaurants.html', cuisine=cuisine)

    return render_template('restaurants_by_cuisine.html', 
                           restaurants_by_cuisine=restaurants_by_cuisine['businesses'], 
                           cuisine=cuisine, page=page, latitude=latitude, longitude=longitude)


@routes.route('/review/<int:id>/delete', methods=['POST'])
@login_required
def delete_review(id):
    review = Review.query.get_or_404(id)
    if review.user_id != current_user.id:
        flash('You do not have permission to delete this review.', category='error')
        return redirect(url_for('routes.restaurant_details', restaurant_id=review.restaurant_id))

    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully!', category='success')
    return redirect(url_for('routes.restaurant_details', restaurant_id=review.restaurant_id))
