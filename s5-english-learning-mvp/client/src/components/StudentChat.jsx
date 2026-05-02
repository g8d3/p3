import { useState, useEffect } from 'react';
import axios from 'axios';

function StudentChat() {
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [message, setMessage] = useState('');
  const [chat, setChat] = useState([]);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchRoles();
  }, []);

  const fetchRoles = async () => {
    try {
      const res = await axios.get('http://localhost:5000/my-roles', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRoles(res.data);
    } catch (error) {
      const errMsg = 'Error fetching roles: ' + (error.response?.data?.error || error.message);
      setError(errMsg);
      console.error(errMsg);
    }
  };

  const handleSend = async () => {
    if (!selectedRole || !message) return;

    setError('');
    try {
      const res = await axios.post('http://localhost:5000/chat', {
        role_id: selectedRole.id,
        message
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setChat([...chat, { user: message, ai: res.data.response }]);
      setMessage('');
    } catch (error) {
      setError('Error sending message: ' + (error.response?.data?.error || error.message));
      console.error('Error sending message:', error);
    }
  };

  return (
    <div>
      <h2>Student Chat</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <select
        value={selectedRole?.id || ''}
        onChange={(e) => setSelectedRole(roles.find(r => r.id == e.target.value) || null)}
      >
        <option value="">Select Role</option>
        {roles.map(r => <option key={r.id} value={r.id}>{r.role_name}</option>)}
      </select>

      {selectedRole && (
        <div>
          <h3>Chatting with {selectedRole.role_name}</h3>
          <div style={{ border: '1px solid #ccc', height: '300px', overflowY: 'scroll' }}>
            {chat.map((msg, i) => (
              <div key={i}>
                <p><strong>You:</strong> {msg.user}</p>
                <p><strong>AI:</strong> {msg.ai}</p>
              </div>
            ))}
          </div>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type your message"
          />
          <button onClick={handleSend}>Send</button>
        </div>
      )}
    </div>
  );
}

export default StudentChat;