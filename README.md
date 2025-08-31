# Portfolio Hub

A modern portfolio website built with Python Flask and MongoDB, featuring drag-and-drop portfolio creation, Discord OAuth2 authentication, and a review system.

## Features

- **Drag & Drop Portfolio Builder**: Create stunning portfolios with an intuitive visual editor
- **Multiple Templates**: Choose from Modern, Creative, Professional, and Developer templates
- **Discord Authentication**: Seamless login with Discord OAuth2
- **Review System**: Rate and review portfolios with star ratings and comments
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **Cloud Storage**: MongoDB database with image upload support
- **Modern UI**: Black and yellow theme with smooth animations

## Quick Start

### Local Development

1. **Clone and Setup**
   ```bash
   cd "portfolio website v1"
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```
   SECRET_KEY=your-secret-key-here
   MONGO_URI=mongodb://localhost:27017/portfolio_db
   DISCORD_CLIENT_ID=your-discord-client-id
   DISCORD_CLIENT_SECRET=your-discord-client-secret
   DISCORD_REDIRECT_URI=http://localhost:5000/auth/discord/callback
   ```

3. **Discord OAuth Setup**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to OAuth2 → General
   - Add redirect URI: `http://localhost:5000/auth/discord/callback`
   - Copy Client ID and Client Secret to your `.env` file

4. **Run the Application**
   ```bash
   python app.py
   ```
   
   Visit `http://localhost:5000`

### Railway Deployment

1. **Prepare for Deployment**
   - Ensure all files are committed to your repository
   - Set up MongoDB Atlas for production database

2. **Deploy to Railway**
   - Connect your GitHub repository to Railway
   - Set environment variables in Railway dashboard:
     - `SECRET_KEY`
     - `MONGO_URI` (MongoDB Atlas connection string)
     - `DISCORD_CLIENT_ID`
     - `DISCORD_CLIENT_SECRET`
     - `DISCORD_REDIRECT_URI` (your Railway domain + `/auth/discord/callback`)

3. **Update Discord OAuth**
   - Add your Railway domain to Discord OAuth redirect URIs
   - Format: `https://your-app.railway.app/auth/discord/callback`

## Project Structure

```
portfolio website v1/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── config.json           # Portfolio templates and elements
├── railway.json          # Railway deployment config
├── Procfile              # Process file for deployment
├── .env.example          # Environment variables template
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Homepage
│   ├── login.html        # Login page
│   ├── portfolios.html   # Portfolio gallery
│   ├── create.html       # Portfolio creation interface
│   ├── edit.html         # Portfolio editing interface
│   └── view_portfolio.html # Portfolio viewing page
└── static/               # Static files
    ├── config.json       # Frontend configuration
    └── uploads/          # User uploaded images
```

## API Endpoints

- `GET /` - Homepage
- `GET /portfolios` - Portfolio gallery
- `GET /create` - Portfolio creation (auth required)
- `GET /edit/<id>` - Portfolio editing (auth required)
- `GET /portfolio/<id>` - View portfolio
- `GET /login` - Login page
- `GET /auth/discord` - Discord OAuth initiation
- `GET /auth/discord/callback` - Discord OAuth callback
- `POST /api/save_portfolio` - Save portfolio data
- `POST /api/upload_image` - Upload image
- `POST /api/submit_review` - Submit portfolio review
- `GET /api/stats` - Get site statistics

## Database Schema

### Users Collection
```javascript
{
  _id: ObjectId,
  discord_id: String,
  username: String,
  avatar: String,
  email: String,
  created_at: Date,
  last_login: Date
}
```

### Portfolios Collection
```javascript
{
  _id: ObjectId,
  title: String,
  template: String,
  background_color: String,
  elements: Array,
  user_id: String,
  username: String,
  created_at: Date,
  updated_at: Date
}
```

### Reviews Collection
```javascript
{
  _id: ObjectId,
  portfolio_id: ObjectId,
  user_id: String,
  username: String,
  rating: Number,
  comment: String,
  created_at: Date
}
```

## Technologies Used

- **Backend**: Python Flask, PyMongo, Flask-Login
- **Database**: MongoDB
- **Authentication**: Discord OAuth2
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Styling**: Custom CSS with black/yellow theme
- **Deployment**: Railway
- **File Upload**: Local storage with Pillow

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support or questions, please open an issue on the GitHub repository.
