const sqlite3 = require('sqlite3').verbose();
const path = require('path');

exports.handler = async (event, context) => {
  // Enable CORS
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
  };

  // Handle preflight requests
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers,
      body: '',
    };
  }

  if (event.httpMethod !== 'GET') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' }),
    };
  }

  try {
    // Connect to database - file should be in the same directory
    const dbPath = path.join(__dirname, 'airbnb.db');
    const db = new sqlite3.Database(dbPath);

    return new Promise((resolve, reject) => {
      // Get all messages grouped by thread_id
      const query = `
        SELECT message_id, thread_id, content, name, host
        FROM messages 
        ORDER BY thread_id, message_id
      `;

      db.all(query, [], (err, rows) => {
        if (err) {
          db.close();
          reject({
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: err.message }),
          });
          return;
        }

        // Group messages by thread_id
        const threadsData = {};
        const threadNames = {};

        rows.forEach(row => {
          const { message_id, thread_id, content, name, host } = row;
          
          // Initialize thread if not exists
          if (!threadsData[thread_id]) {
            threadsData[thread_id] = [];
          }

          // Store first guest name as thread name
          if (!host && !threadNames[thread_id]) {
            threadNames[thread_id] = name;
          }

          // Format message for API response
          const messageData = {
            role: host ? 'host' : 'guest',
            text: content,
            name: name,
            time: 'Recent'
          };

          threadsData[thread_id].push(messageData);
        });

        db.close();

        resolve({
          statusCode: 200,
          headers,
          body: JSON.stringify({
            threads: threadNames,
            messages: threadsData
          }),
        });
      });
    });

  } catch (error) {
    console.error('Error fetching threads from database:', error);
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: error.message }),
    };
  }
};
