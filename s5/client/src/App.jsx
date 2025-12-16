import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Login from './components/Login';
import TeacherDashboard from './components/TeacherDashboard';
import StudentChat from './components/StudentChat';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/teacher" element={<TeacherDashboard />} />
          <Route path="/student" element={<StudentChat />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;