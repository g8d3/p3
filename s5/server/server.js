const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const axios = require('axios');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// SQLite database setup
const db = new sqlite3.Database('./english_learning.db', (err) => {
  if (err) {
    console.error('Error opening database:', err.message);
  } else {
    console.log('Connected to the SQLite database.');
    // Create tables
    db.serialize(() => {
      db.run(`CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
      )`);

      db.run(`CREATE TABLE IF NOT EXISTS ai_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        role_name TEXT,
        api_key TEXT,
        model_id TEXT,
        base_url TEXT,
        api_endpoint TEXT DEFAULT '/chat/completions',
        FOREIGN KEY (teacher_id) REFERENCES users (id)
      )`);

      db.run(`CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        teacher_id INTEGER,
        student_id INTEGER,
        ai_role_id INTEGER,
        FOREIGN KEY (teacher_id) REFERENCES users (id),
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (ai_role_id) REFERENCES ai_roles (id)
      )`);

      db.run(`CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        ai_role_id INTEGER,
        messages TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (ai_role_id) REFERENCES ai_roles (id)
      )`);

      db.run(`CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        chat_id INTEGER,
        analysis TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES users (id),
        FOREIGN KEY (chat_id) REFERENCES chats (id)
      )`);
    });
  }
});

// Basic route
app.get('/', (req, res) => {
  res.send('English Learning API');
});

// Auth routes
app.post('/register', async (req, res) => {
  const { username, password, role } = req.body;
  if (!username || !password || !['student', 'teacher'].includes(role)) {
    return res.status(400).json({ error: 'Invalid input' });
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  db.run(`INSERT INTO users (username, password, role) VALUES (?, ?, ?)`, [username, hashedPassword, role], function(err) {
    if (err) {
      return res.status(400).json({ error: 'User already exists' });
    }
    res.status(201).json({ message: 'User created' });
  });
});

app.post('/login', (req, res) => {
  const { username, password } = req.body;

  db.get(`SELECT * FROM users WHERE username = ?`, [username], async (err, user) => {
    if (err || !user) {
      return res.status(400).json({ error: 'User not found' });
    }

    const isValid = await bcrypt.compare(password, user.password);
    if (!isValid) {
      return res.status(400).json({ error: 'Invalid password' });
    }

    const token = jwt.sign({ id: user.id, role: user.role }, process.env.JWT_SECRET || 'secret');
    res.json({ token });
  });
});

// Middleware to verify token
const authenticate = (req, res, next) => {
  const token = req.header('Authorization')?.replace('Bearer ', '');
  console.log('Authenticating token:', token ? 'present' : 'missing');
  if (!token) {
    console.log('No token provided');
    return res.status(401).json({ error: 'Access denied' });
  }

  jwt.verify(token, process.env.JWT_SECRET || 'secret', (err, user) => {
    if (err) {
      console.error('Token verification error:', err);
      return res.status(403).json({ error: 'Invalid token' });
    }
    console.log('Authenticated user:', user);
    req.user = user;
    next();
  });
};

// AI Roles routes (protected)
app.post('/roles', authenticate, (req, res) => {
  console.log('Creating role for user:', req.user);
  if (req.user.role !== 'teacher') {
    console.log('Access denied: user role is', req.user.role);
    return res.status(403).json({ error: 'Access denied' });
  }

  const { role_name, api_key, model_id, base_url, api_endpoint } = req.body;
  console.log('Received role data:', { role_name, api_key: api_key ? '***' : '', model_id, base_url, api_endpoint });
  if (!role_name || !api_key || !model_id || !base_url) {
    return res.status(400).json({ error: 'Role name, API key, model ID, and base URL are required' });
  }

  const endpoint = api_endpoint || '/chat/completions';

  db.run(`INSERT INTO ai_roles (teacher_id, role_name, api_key, model_id, base_url, api_endpoint) VALUES (?, ?, ?, ?, ?, ?)`,
    [req.user.id, role_name, api_key, model_id, base_url, endpoint], function(err) {
      if (err) {
        console.error('Database error creating role:', err);
        return res.status(500).json({ error: 'Error creating role: ' + err.message });
      }
      console.log('Role created with ID:', this.lastID);
      res.status(201).json({ id: this.lastID });
    });
});

app.get('/roles', authenticate, (req, res) => {
  db.all(`SELECT * FROM ai_roles WHERE teacher_id = ?`, [req.user.id], (err, rows) => {
    if (err) return res.status(500).json({ error: 'Error fetching roles' });
    res.json(rows);
  });
});

// Assignments
app.post('/assign', authenticate, (req, res) => {
  if (req.user.role !== 'teacher') return res.status(403).json({ error: 'Access denied' });

  const { student_id, ai_role_id } = req.body;
  db.run(`INSERT INTO assignments (teacher_id, student_id, ai_role_id) VALUES (?, ?, ?)`,
    [req.user.id, student_id, ai_role_id], function(err) {
      if (err) return res.status(500).json({ error: 'Error assigning role' });
      res.status(201).json({ message: 'Assigned' });
    });
});

app.get('/students', authenticate, (req, res) => {
  if (req.user.role !== 'teacher') return res.status(403).json({ error: 'Access denied' });

  db.all(`SELECT id, username FROM users WHERE role = 'student'`, [], (err, rows) => {
    if (err) return res.status(500).json({ error: 'Error fetching students' });
    res.json(rows);
  });
});

app.get('/progress', authenticate, (req, res) => {
  if (req.user.role !== 'teacher') return res.status(403).json({ error: 'Access denied' });

  db.all(`SELECT p.*, u.username, r.role_name FROM progress p JOIN users u ON p.student_id = u.id JOIN chats c ON p.chat_id = c.id JOIN ai_roles r ON c.ai_role_id = r.id WHERE r.teacher_id = ?`,
    [req.user.id], (err, rows) => {
      if (err) return res.status(500).json({ error: 'Error fetching progress' });
      res.json(rows);
    });
});

// For students
app.get('/my-roles', authenticate, (req, res) => {
  if (req.user.role !== 'student') return res.status(403).json({ error: 'Access denied' });

  db.all(`SELECT a.id, r.role_name, r.api_key, r.model_id, r.base_url, r.api_endpoint FROM assignments a JOIN ai_roles r ON a.ai_role_id = r.id WHERE a.student_id = ?`,
    [req.user.id], (err, rows) => {
      if (err) return res.status(500).json({ error: 'Error fetching roles' });
      res.json(rows);
    });
});

// Chat
app.post('/chat', authenticate, async (req, res) => {
  if (req.user.role !== 'student') return res.status(403).json({ error: 'Access denied' });

  const { role_id, message } = req.body;
  if (!role_id || !message) return res.status(400).json({ error: 'Missing role_id or message' });

  db.get(`SELECT r.* FROM assignments a JOIN ai_roles r ON a.ai_role_id = r.id WHERE a.student_id = ? AND a.ai_role_id = ?`,
    [req.user.id, role_id], async (err, role) => {
      if (err) {
        console.error('Database error fetching role:', err);
        return res.status(500).json({ error: 'Database error' });
      }
      if (!role) return res.status(404).json({ error: 'Role not assigned to you' });

      try {
        const url = role.base_url.replace(/\/$/, '') + role.api_endpoint;
        console.log('Calling AI API:', url, 'with model:', role.model_id);
        const response = await axios.post(url, {
          model: role.model_id,
          messages: [{ role: 'user', content: message }]
        }, {
          headers: {
            'Authorization': `Bearer ${role.api_key}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.data.choices || !response.data.choices[0]) {
          console.error('Unexpected AI response format:', response.data);
          return res.status(500).json({ error: 'Unexpected AI response format' });
        }

        const aiResponse = response.data.choices[0].message.content;

        // Store chat
        db.run(`INSERT INTO chats (student_id, ai_role_id, messages) VALUES (?, ?, ?)`,
          [req.user.id, role_id, JSON.stringify([{ user: message, ai: aiResponse }])], function(err) {
            if (err) {
              console.error('Error storing chat:', err);
            }
            const chatId = this.lastID;

            // Analyze progress
            const analysisUrl = role.base_url.replace(/\/$/, '') + role.api_endpoint;
            console.log('Calling AI for analysis:', analysisUrl);
            axios.post(analysisUrl, {
              model: role.model_id,
              messages: [{ role: 'system', content: 'Analyze the following English conversation and provide feedback on the student\'s language proficiency, grammar, vocabulary, and suggest improvements.' }, { role: 'user', content: `User: ${message}\nAI: ${aiResponse}` }]
            }, {
              headers: {
                'Authorization': `Bearer ${role.api_key}`,
                'Content-Type': 'application/json'
              }
            }).then(analysisRes => {
              if (analysisRes.data.choices && analysisRes.data.choices[0]) {
                const analysis = analysisRes.data.choices[0].message.content;
                db.run(`INSERT INTO progress (student_id, chat_id, analysis) VALUES (?, ?, ?)`,
                  [req.user.id, chatId, analysis], function(err) {
                    if (err) console.error('Error storing progress:', err);
                  });
              } else {
                console.error('Unexpected analysis response:', analysisRes.data);
              }
            }).catch(err => console.error('Analysis error details:', {
              url: analysisUrl,
              status: err.response?.status,
              data: err.response?.data,
              message: err.message
            }));
          });

        res.json({ response: aiResponse });
      } catch (error) {
        console.error('AI service error details:', {
          url: `${role.base_url}${role.api_endpoint}`,
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        });
        res.status(500).json({ error: `AI service error (${error.response?.status}): ${error.response?.data?.error || error.message}` });
      }
    });
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = app;