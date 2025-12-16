import { useState, useEffect } from 'react';
import axios from 'axios';

function TeacherDashboard() {
  const [roles, setRoles] = useState([]);
  const [students, setStudents] = useState([]);
  const [progress, setProgress] = useState([]);
  const [roleForm, setRoleForm] = useState({ role_name: '', api_key: '', model_id: '', base_url: '', api_endpoint: '/chat/completions' });
  const [assignForm, setAssignForm] = useState({ student_id: '', ai_role_id: '' });
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');

  useEffect(() => {
    fetchRoles();
    fetchStudents();
    fetchProgress();
  }, []);

  const fetchRoles = async () => {
    try {
      const res = await axios.get('http://localhost:5000/roles', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRoles(res.data);
    } catch (error) {
      const errMsg = 'Error fetching roles: ' + (error.response?.data?.error || error.message);
      setError(errMsg);
      console.error(errMsg);
    }
  };

  const fetchStudents = async () => {
    try {
      const res = await axios.get('http://localhost:5000/students', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStudents(res.data);
    } catch (error) {
      const errMsg = 'Error fetching students: ' + (error.response?.data?.error || error.message);
      setError(errMsg);
      console.error(errMsg);
    }
  };

  const fetchProgress = async () => {
    try {
      const res = await axios.get('http://localhost:5000/progress', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setProgress(res.data);
    } catch (error) {
      const errMsg = 'Error fetching progress: ' + (error.response?.data?.error || error.message);
      setError(errMsg);
      console.error(errMsg);
    }
  };

  const handleCreateRole = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post('http://localhost:5000/roles', roleForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setRoleForm({ role_name: '', api_key: '', model_id: '', base_url: '', api_endpoint: '/chat/completions' });
      fetchRoles();
    } catch (error) {
      setError('Error creating role: ' + (error.response?.data?.error || error.message));
      console.error('Error creating role:', error);
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post('http://localhost:5000/assign', assignForm, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAssignForm({ student_id: '', ai_role_id: '' });
    } catch (error) {
      setError('Error assigning: ' + (error.response?.data?.error || error.message));
      console.error('Error assigning:', error);
    }
  };

  return (
    <div>
      <h2>Teacher Dashboard</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <h3>Create AI Role</h3>
      <form onSubmit={handleCreateRole}>
        <input
          type="text"
          placeholder="Role Name"
          value={roleForm.role_name}
          onChange={(e) => setRoleForm({ ...roleForm, role_name: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API Key"
          value={roleForm.api_key}
          onChange={(e) => setRoleForm({ ...roleForm, api_key: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="Model ID"
          value={roleForm.model_id}
          onChange={(e) => setRoleForm({ ...roleForm, model_id: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="Base URL"
          value={roleForm.base_url}
          onChange={(e) => setRoleForm({ ...roleForm, base_url: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="API Endpoint (e.g., /chat/completions)"
          value={roleForm.api_endpoint}
          onChange={(e) => setRoleForm({ ...roleForm, api_endpoint: e.target.value.replace(/^\/*/, '/') })}
        />
        <button type="submit">Create Role</button>
      </form>

      <h3>Assign Role to Student</h3>
      <form onSubmit={handleAssign}>
        <select
          value={assignForm.student_id}
          onChange={(e) => setAssignForm({ ...assignForm, student_id: e.target.value })}
          required
        >
          <option value="">Select Student</option>
          {students.map(s => <option key={s.id} value={s.id}>{s.username}</option>)}
        </select>
        <select
          value={assignForm.ai_role_id}
          onChange={(e) => setAssignForm({ ...assignForm, ai_role_id: e.target.value })}
          required
        >
          <option value="">Select Role</option>
          {roles.map(r => <option key={r.id} value={r.id}>{r.role_name}</option>)}
        </select>
        <button type="submit">Assign</button>
      </form>

      <h3>My Roles</h3>
      <ul>
        {roles.map(r => <li key={r.id}>{r.role_name}</li>)}
      </ul>

      <h3>Student Progress</h3>
      <div>
        {progress.map(p => (
          <div key={p.id} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
            <p><strong>Student:</strong> {p.username}</p>
            <p><strong>Role:</strong> {p.role_name}</p>
            <p><strong>Analysis:</strong> {p.analysis}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default TeacherDashboard;