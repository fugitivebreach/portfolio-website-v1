from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
import requests
import json
from datetime import datetime, timezone
from bson.objectid import ObjectId
from dotenv import load_dotenv
import base64

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/portfolio_db')
app.config['MONGO_DBNAME'] = 'portfolio_db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Discord OAuth2 settings
DISCORD_CLIENT_ID = os.environ.get('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.environ.get('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', 'http://localhost:5000/auth/discord/callback')

# Admin configuration
ADMIN_USER_IDS = ['1317342800941023242']  # Discord user IDs with admin access

# User tags configuration
USER_TAGS = {
    '1317342800941023242': {'name': 'Founder', 'color': '#415C92'},
    # Add more users like: 'discord_id': {'name': 'TagName', 'color': '#hexcolor'}
}

try:
    mongo = PyMongo(app)
    # Test the connection with a simple operation
    if mongo.db is not None:
        mongo.db.command('ping')
        print("✅ MongoDB connection successful!")
    else:
        print("❌ MongoDB connection failed: db is None")
        mongo = None
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    mongo = None

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['discord_id']
        self.username = user_data['username']
        self.avatar = user_data.get('avatar')
        self.email = user_data.get('email')
        self.last_login = user_data.get('last_login')
        self.is_admin = str(self.id) in ADMIN_USER_IDS
        self.restrictions = user_data.get('restrictions', {})
        self.profile_visibility = user_data.get('profile_visibility', 'public')
        self.tag = USER_TAGS.get(str(self.id))

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({'discord_id': user_id})
    if user_data:
        return User(user_data)
    return None

@app.before_request
def check_user_restrictions():
    # Skip restriction checks for auth routes and static files
    if request.endpoint in ['auth', 'auth_callback', 'logout'] or request.path.startswith('/static'):
        return
    
    # Check if user is blocked from site access
    if current_user.is_authenticated and current_user.restrictions.get('block_site'):
        logout_user()
        flash('Your account has been restricted from accessing this site.', 'error')
        return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/portfolios')
def portfolios():
    # Get all portfolios sorted by average rating (highest to lowest)
    pipeline = [
        {
            '$lookup': {
                'from': 'reviews',
                'localField': '_id',
                'foreignField': 'portfolio_id',
                'as': 'reviews'
            }
        },
        {
            '$addFields': {
                'avg_rating': {
                    '$cond': {
                        'if': {'$gt': [{'$size': '$reviews'}, 0]},
                        'then': {'$avg': '$reviews.rating'},
                        'else': 0
                    }
                },
                'review_count': {'$size': '$reviews'}
            }
        },
        {
            '$sort': {'avg_rating': -1, 'created_at': -1}
        }
    ]
    
    portfolios = list(mongo.db.portfolios.aggregate(pipeline))
    return render_template('portfolios.html', portfolios=portfolios)

@app.route('/create')
@login_required
def create():
    # Check if user is blocked from creating portfolios
    if current_user.restrictions.get('block_portfolios') or current_user.restrictions.get('block_site'):
        flash('You are restricted from creating portfolios.', 'error')
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/edit/<portfolio_id>')
@login_required
def edit_portfolio(portfolio_id):
    # Check if user is blocked from creating/editing portfolios
    if current_user.restrictions.get('block_portfolios') or current_user.restrictions.get('block_site'):
        flash('You are restricted from editing portfolios.', 'error')
        return redirect(url_for('index'))
    
    portfolio = mongo.db.portfolios.find_one({'_id': ObjectId(portfolio_id), 'user_id': current_user.id})
    if not portfolio:
        flash('Portfolio not found or you do not have permission to edit it.', 'error')
        return redirect(url_for('portfolios'))
    return render_template('edit.html', portfolio=portfolio)

@app.route('/portfolio/<portfolio_id>')
def view_portfolio(portfolio_id):
    portfolio = mongo.db.portfolios.find_one({'_id': ObjectId(portfolio_id)})
    if not portfolio:
        flash('Portfolio not found.', 'error')
        return redirect(url_for('portfolios'))
    
    reviews = list(mongo.db.reviews.find({'portfolio_id': ObjectId(portfolio_id)}).sort('created_at', -1))
    return render_template('view_portfolio.html', portfolio=portfolio, reviews=reviews)

@app.route('/api/save_portfolio', methods=['POST'])
@login_required
def save_portfolio():
    # Check if user is blocked from creating/editing portfolios
    if current_user.restrictions.get('block_portfolios') or current_user.restrictions.get('block_site'):
        return jsonify({'success': False, 'error': 'You are restricted from creating or editing portfolios'})
    
    data = request.get_json()
    
    portfolio_data = {
        'title': data.get('title', 'Untitled Portfolio'),
        'template': data.get('template', 'default'),
        'background_color': data.get('background_color', '#000000'),
        'elements': data.get('elements', []),
        'user_id': current_user.id,
        'username': current_user.username,
        'updated_at': datetime.utcnow()
    }
    
    portfolio_id = data.get('portfolio_id')
    if portfolio_id:
        # Update existing portfolio
        try:
            result = mongo.db.portfolios.update_one(
                {'_id': ObjectId(portfolio_id), 'user_id': current_user.id},
                {'$set': portfolio_data}
            )
            if result.matched_count:
                return jsonify({'success': True, 'portfolio_id': portfolio_id})
            else:
                return jsonify({'success': False, 'error': 'Portfolio not found or access denied'})
        except Exception as e:
            return jsonify({'success': False, 'error': 'Failed to submit review'})
    else:
        # Create new portfolio
        try:
            portfolio_data['created_at'] = datetime.now(timezone.utc)
            result = mongo.db.portfolios.insert_one(portfolio_data)
            return jsonify({'success': True, 'portfolio_id': str(result.inserted_id)})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Failed to create portfolio: {str(e)}'})

@app.route('/api/upload_image', methods=['POST'])
@login_required
def upload_image():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        return jsonify({'success': True, 'url': f'/static/uploads/{filename}'})
    
    return jsonify({'success': False, 'error': 'Invalid file type'})

@app.route('/api/submit_review', methods=['POST'])
@login_required
def submit_review():
    # Check if user is blocked from creating reviews
    if current_user.restrictions.get('block_reviews') or current_user.restrictions.get('block_site'):
        return jsonify({'success': False, 'error': 'You are restricted from submitting reviews'})
    
    data = request.get_json()
    
    # Check if user already reviewed this portfolio
    existing_review = mongo.db.reviews.find_one({
        'portfolio_id': ObjectId(data['portfolio_id']),
        'user_id': current_user.id
    })
    
    if existing_review:
        return jsonify({'success': False, 'error': 'You have already reviewed this portfolio'})
    
    review_data = {
        'portfolio_id': ObjectId(data['portfolio_id']),
        'user_id': current_user.id,
        'username': current_user.username,
        'rating': int(data['rating']),
        'comment': data.get('comment', ''),
        'created_at': datetime.utcnow()
    }
    
    mongo.db.reviews.insert_one(review_data)
    return jsonify({'success': True})

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/auth/discord')
def discord_auth():
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20email"
    return redirect(discord_auth_url)

@app.route('/auth/discord/callback')
def discord_callback():
    code = request.args.get('code')
    if not code:
        flash('Authentication failed.', 'error')
        return redirect(url_for('login'))
    
    # Exchange code for access token
    token_data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    token_response = requests.post('https://discord.com/api/oauth2/token', data=token_data)
    token_json = token_response.json()
    
    if 'access_token' not in token_json:
        flash('Authentication failed.', 'error')
        return redirect(url_for('login'))
    
    # Get user info from Discord
    headers = {'Authorization': f"Bearer {token_json['access_token']}"}
    user_response = requests.get('https://discord.com/api/users/@me', headers=headers)
    user_data = user_response.json()
    
    # Check if user exists in database
    if not mongo:
        flash('Database connection error. Please try again later.', 'error')
        return redirect(url_for('login'))
    
    existing_user = mongo.db.users.find_one({'discord_id': user_data['id']})
    
    if existing_user:
        # Update user info
        mongo.db.users.update_one(
            {'discord_id': user_data['id']},
            {'$set': {
                'username': user_data['username'],
                'avatar': user_data.get('avatar'),
                'email': user_data.get('email'),
                'last_login': datetime.utcnow()
            }}
        )
        user = User(existing_user)
    else:
        # Create new user
        new_user_data = {
            'discord_id': user_data['id'],
            'username': user_data['username'],
            'avatar': user_data.get('avatar'),
            'email': user_data.get('email'),
            'description': '',
            'profile_visibility': 'public',
            'created_at': datetime.now(timezone.utc),
            'last_login': datetime.now(timezone.utc)
        }
        result = mongo.db.users.insert_one(new_user_data)
        new_user_data['_id'] = result.inserted_id
        user = User(new_user_data)
    
    login_user(user)
    flash('Successfully logged in!', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    # Get user's portfolios
    user_portfolios = list(mongo.db.portfolios.find({'user_id': current_user.id}))
    return render_template('profile.html', user=current_user, portfolios=user_portfolios)

@app.route('/profile/<user_id>')
def public_profile(user_id):
    try:
        # Try to find by discord_id first (for direct discord ID links)
        user_data = mongo.db.users.find_one({'discord_id': user_id})
        
        # If not found, try by MongoDB ObjectId (for legacy links)
        if not user_data:
            try:
                user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            except:
                pass
        
        if not user_data or user_data.get('profile_visibility') == 'private':
            flash('Profile not found or private.', 'error')
            return redirect(url_for('index'))
        
        user = User(user_data)
        user_portfolios = list(mongo.db.portfolios.find({'user_id': user_data['discord_id']}))
        return render_template('public_profile.html', user=user, portfolios=user_portfolios)
    except:
        flash('Profile not found.', 'error')
        return redirect(url_for('index'))

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    
    update_data = {}
    if 'description' in data:
        update_data['description'] = data['description']
    if 'profile_visibility' in data:
        update_data['profile_visibility'] = data['profile_visibility']
    
    if update_data:
        mongo.db.users.update_one(
            {'discord_id': current_user.id},
            {'$set': update_data}
        )
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'No data to update'})

@app.route('/api/delete_portfolio', methods=['POST'])
@login_required
def delete_portfolio():
    data = request.get_json()
    portfolio_id = data.get('portfolio_id')
    
    if not portfolio_id:
        return jsonify({'success': False, 'error': 'Portfolio ID required'})
    
    result = mongo.db.portfolios.delete_one({
        '_id': ObjectId(portfolio_id),
        'user_id': current_user.id
    })
    
    if result.deleted_count:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Portfolio not found or unauthorized'})

@app.route('/logout')
def logout():
    logout_user()
    flash('Successfully logged out!', 'info')
    return redirect(url_for('index'))

@app.route('/api/stats')
def get_stats():
    try:
        portfolio_count = mongo.db.portfolios.count_documents({})
        user_count = mongo.db.users.count_documents({})
        review_count = mongo.db.reviews.count_documents({})
        
        return jsonify({
            'portfolios': portfolio_count,
            'users': user_count,
            'reviews': review_count
        })
    except Exception as e:
        return jsonify({
            'portfolios': 0,
            'users': 0,
            'reviews': 0
        })

# Admin decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin():
    return render_template('admin.html')

@app.route('/api/admin/search_users', methods=['POST'])
@login_required
@admin_required
def admin_search_users():
    data = request.get_json()
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({'success': False, 'error': 'Search query required'})
    
    try:
        # Search by username or Discord ID
        search_filter = {
            '$or': [
                {'username': {'$regex': query, '$options': 'i'}},
                {'discord_id': {'$regex': query, '$options': 'i'}}
            ]
        }
        
        users = list(mongo.db.users.find(search_filter).limit(20))
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            user['_id'] = str(user['_id'])
            if 'created_at' in user:
                user['created_at'] = user['created_at'].isoformat()
        
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/restrict_user', methods=['POST'])
@login_required
@admin_required
def admin_restrict_user():
    data = request.get_json()
    user_id = data.get('user_id')
    restrictions = data.get('restrictions', {})
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'})
    
    try:
        restriction_data = {
            'reason': restrictions.get('reason', ''),
            'block_reviews': restrictions.get('block_reviews', False),
            'block_portfolios': restrictions.get('block_portfolios', False),
            'block_site': restrictions.get('block_site', False),
            'permanent': restrictions.get('permanent', False),
            'applied_at': datetime.now(timezone.utc),
            'applied_by': current_user.username
        }
        
        result = mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'restrictions': restriction_data}}
        )
        
        if result.matched_count:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/remove_restrictions', methods=['POST'])
@login_required
@admin_required
def admin_remove_restrictions():
    data = request.get_json()
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'success': False, 'error': 'User ID required'})
    
    try:
        result = mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$unset': {'restrictions': ''}}
        )
        
        if result.matched_count:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/admin/delete_portfolio', methods=['POST'])
@login_required
@admin_required
def admin_delete_portfolio():
    data = request.get_json()
    portfolio_input = data.get('portfolio_id')
    
    if not portfolio_input:
        return jsonify({'success': False, 'error': 'Portfolio ID or URL required'})
    
    try:
        # Extract portfolio ID from URL if needed
        portfolio_id = portfolio_input
        if '/portfolio/' in portfolio_input:
            portfolio_id = portfolio_input.split('/portfolio/')[-1]
        
        # Delete portfolio
        portfolio_result = mongo.db.portfolios.delete_one({'_id': ObjectId(portfolio_id)})
        
        # Delete associated reviews
        reviews_result = mongo.db.reviews.delete_many({'portfolio_id': ObjectId(portfolio_id)})
        
        if portfolio_result.deleted_count:
            return jsonify({
                'success': True, 
                'message': f'Portfolio deleted. Also removed {reviews_result.deleted_count} associated reviews.'
            })
        else:
            return jsonify({'success': False, 'error': 'Portfolio not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
