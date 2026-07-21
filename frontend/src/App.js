import React, { useState, useEffect } from "react";
import Dashboard from "./Dashboard";
import SubmitTask from "./SubmitTask";
import Login from "./Login";
import Register from "./Register";
import { isAuthenticated, logout, AUTH_EXPIRED_EVENT } from "./api";
import { motion } from "framer-motion";

function App() {
  const [tasks, setTasks] = useState([]);
  const [loggedIn, setLoggedIn] = useState(isAuthenticated());
  const [authView, setAuthView] = useState("login"); // "login" | "register"
  const [authNotice, setAuthNotice] = useState(null);

  const handleTaskSubmitted = (newTask) => {
    // Add the new task to the top of the list for immediate feedback
    setTasks(prevTasks => [newTask, ...prevTasks]);
  };

  const handleLoginSuccess = () => {
    setAuthNotice(null);
    setLoggedIn(true);
  };

  // register() (backend's POST /auth/register) doesn't return a token -
  // only a confirmation message - so "auto-login" would mean silently
  // firing a second API call (login()) right after, with its own
  // separate failure mode to handle (e.g. already at the 5/minute rate
  // limit from testing registration). Routing back to Login instead
  // keeps the two flows independent, and doubles as a visible
  // confirmation that registration actually worked.
  const handleRegisterSuccess = () => {
    setAuthView("login");
    setAuthNotice("Account created - please log in.");
  };

  const handleLogout = () => {
    logout();
    setTasks([]);
    setAuthView("login");
    setAuthNotice(null);
    setLoggedIn(false);
  };

  // Fired by api/index.js whenever the app decides the session is no
  // longer valid - either an authenticated call coming back 401, or
  // (Dashboard's SSE connection) the stored JWT's own exp claim having
  // passed. Listening here, rather than only reacting locally in
  // whichever component triggered it, means ANY part of the app
  // discovering the session is dead bounces the whole UI back to Login,
  // not just the one panel that happened to notice first.
  useEffect(() => {
    const handleAuthExpired = () => {
      setTasks([]);
      setAuthView("login");
      setAuthNotice("Your session expired. Please log in again.");
      setLoggedIn(false);
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, []);

  return (
    <motion.div
      className="bg-gray-900 text-white min-h-screen"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <header className="bg-gray-800/50 backdrop-blur-sm p-4 sticky top-0 z-10 shadow-lg">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-3xl font-bold text-cyan-300 drop-shadow-lg">
            GridForge
          </h1>
          {loggedIn && (
            <button
              onClick={handleLogout}
              className="text-sm text-gray-400 hover:text-red-400 transition-colors"
            >
              Log out
            </button>
          )}
        </div>
      </header>
      <main className="p-4 sm:p-8 max-w-7xl mx-auto">
        {loggedIn ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-1">
              <SubmitTask onTaskSubmitted={handleTaskSubmitted} />
            </div>
            <div className="lg:col-span-2">
              <Dashboard tasks={tasks} setTasks={setTasks} />
            </div>
          </div>
        ) : authView === "login" ? (
          <Login
            notice={authNotice}
            onLoginSuccess={handleLoginSuccess}
            onSwitchToRegister={() => {
              setAuthView("register");
              setAuthNotice(null);
            }}
          />
        ) : (
          <Register
            onRegisterSuccess={handleRegisterSuccess}
            onSwitchToLogin={() => {
              setAuthView("login");
              setAuthNotice(null);
            }}
          />
        )}
      </main>
    </motion.div>
  );
}

export default App;
