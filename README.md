# OpenTrader

A modern trading platform for journaling, analysis, and performance tracking.

## Features

- Trade journaling with detailed trade tracking
- Advanced analytics and performance metrics
- Real-time trade tracking
- Customizable templates and trading plans
- Modern, responsive UI built with React and Material-UI

## Tech Stack

- **Frontend**: React, Redux Toolkit, Material-UI
- **Backend**: Node.js, Express, Mongoose, MongoDB
- **Authentication**: JWT
- **Charts**: Chart.js

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- MongoDB

### Installation

1. **Clone the repository**

2. **Install dependencies**
   Install dependencies for the root, server, and client.
   ```bash
   # Install root dependencies (for running client/server concurrently)
   npm install

   # Install server dependencies
   cd server
   npm install

   # Install client dependencies
   cd ../client
   npm install
   cd ..
   ```

3. **Set up environment variables**
   Create a `.env` file in the `server/` directory with the following variables:
   ```
   PORT=5000
   MONGODB_URI=your_mongodb_connection_string
   JWT_SECRET=your_jwt_secret_key_here
   ```

### Running the Application

Start both the backend and frontend servers concurrently from the root directory:
```bash
npm run dev
```
The application will be available at `http://localhost:3000`. The server will run on `http://localhost:5000`.

## Project Structure

```
open-trader/
├── client/                 # Frontend React application
│   ├── public/            # Public assets
│   └── src/               # Source code
│       ├── components/    # React components
│       ├── store/         # Redux store and slices
│       └── index.js       # Entry point
├── server/                # Backend Node.js application
│   ├── models/           # MongoDB models
│   ├── routes/           # API routes
│   └── index.js          # Server entry point
└── package.json          # Project dependencies
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details
