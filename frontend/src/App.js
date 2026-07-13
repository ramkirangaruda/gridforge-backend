import React, { useState } from "react";
import Dashboard from "./Dashboard";
import SubmitTask from "./SubmitTask";
import { motion } from "framer-motion";

function App() {
  const [tasks, setTasks] = useState([]);

  const handleTaskSubmitted = (newTask) => {
    // Add the new task to the top of the list for immediate feedback
    setTasks(prevTasks => [newTask, ...prevTasks]);
  };

  return (
    <motion.div
      className="bg-gray-900 text-white min-h-screen"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <header className="bg-gray-800/50 backdrop-blur-sm p-4 sticky top-0 z-10 shadow-lg">
        <h1 className="text-3xl font-bold text-center text-cyan-300 drop-shadow-lg">
          GridForge
        </h1>
      </header>
      <main className="p-4 sm:p-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <SubmitTask onTaskSubmitted={handleTaskSubmitted} />
          </div>
          <div className="lg:col-span-2">
            <Dashboard tasks={tasks} setTasks={setTasks} />
          </div>
        </div>
      </main>
    </motion.div>
  );
}

export default App;
