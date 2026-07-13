import React, { useEffect, useState } from "react";
import { getTasks } from "./api";
import { motion, AnimatePresence } from "framer-motion";

const statusColors = {
    queued: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    running: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    completed: "bg-green-500/20 text-green-300 border-green-500/30",
    failed: "bg-red-500/20 text-red-300 border-red-500/30",
};

const TaskCard = ({ task }) => {
    const statusClass = statusColors[task.status] || "bg-gray-500/20 text-gray-300 border-gray-500/30";
    const [isExpanded, setIsExpanded] = useState(false);

    const formatTime = (isoString) => {
        if (!isoString) return "N/A";
        return new Date(isoString).toLocaleString();
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="bg-gray-800/50 backdrop-blur-sm rounded-xl shadow-lg p-5 border border-gray-700"
            onClick={() => setIsExpanded(!isExpanded)}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex flex-wrap items-center gap-3">
                    <span className={`px-3 py-1 text-sm font-medium rounded-full border ${statusClass}`}>
                        {task.status}
                        {task.status === "running" && <span className="animate-pulse">...</span>}
                    </span>
                    <span className="text-sm text-gray-400">{task.filename}</span>
                </div>
                <div className="text-xs text-gray-400 font-mono break-all text-right">
                    {task.id}
                </div>
            </div>

            <div className="mt-3 text-sm text-gray-300 grid grid-cols-2 gap-2">
                <div><span className="text-gray-400 font-semibold">Created:</span> {formatTime(task.created_at)}</div>
                <div><span className="text-gray-400 font-semibold">Completed:</span> {formatTime(task.completed_at)}</div>
            </div>

            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-4 overflow-hidden"
                    >
                        <p className="text-sm font-bold text-gray-400 mb-2">Logs:</p>
                        <pre className="bg-black rounded-md p-4 text-sm text-gray-300 font-mono overflow-auto max-h-60">
                            <code>{task.logs || "No logs yet."}</code>
                        </pre>
                        {task.exit_code !== null && (
                            <p className="text-sm mt-2">
                                <span className="font-bold text-gray-400">Exit Code:</span> {task.exit_code}
                            </p>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
};


function Dashboard({ tasks, setTasks }) {
    const [error, setError] = useState(null);

    const fetchTasks = async () => {
        try {
            const res = await getTasks();
            setTasks(res);
            setError(null);
        } catch (err) {
            console.error(err);
            setError("Failed to fetch tasks. Is the backend running?");
        }
    };

    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="space-y-4">
            <h2 className="text-2xl font-bold text-cyan-300">Task Dashboard</h2>
            {error && <div className="text-center py-4 text-red-400">{error}</div>}
            <AnimatePresence>
                {tasks.length > 0 ? (
                    tasks.map((task) => (
                        <TaskCard key={task.id} task={task} />
                    ))
                ) : (
                    <div className="text-center py-10 text-gray-500">
                        No tasks yet. Submit a project to get started!
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default Dashboard;