import React, { useState } from 'react';
import LogsPanel from './LogsPanel';

const TaskItem = ({ task }) => {
    const [expanded, setExpanded] = useState(false);

    const getStatusColor = (status) => {
        switch (status) {
            case 'completed':
                return 'text-green-400 border-green-400';
            case 'failed':
                return 'text-red-400 border-red-400';
            case 'running':
                return 'text-yellow-400 border-yellow-400';
            case 'queued':
            default:
                return 'text-gray-400 border-gray-400';
        }
    };

    const formatTime = (isoString) => {
        if (!isoString) return 'N/A';
        return new Date(isoString).toLocaleString();
    };

    return (
        <div className="bg-gray-900 p-4 rounded-lg border border-gray-700">
            <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(!expanded)}>
                <div>
                    <p className="font-mono text-sm text-cyan-400">{task.id}</p>
                    <p className="font-semibold">{task.filename}</p>
                </div>
                <div className="flex items-center space-x-4">
                    <span className={`px-2 py-1 text-xs font-bold rounded-full border ${getStatusColor(task.status)}`}>
                        {task.status.toUpperCase()}
                    </span>
                    <button className="text-gray-400 hover:text-white">
                        {expanded ? '▼' : '▶'}
                    </button>
                </div>
            </div>
            {expanded && (
                <div className="mt-4 border-t border-gray-700 pt-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-gray-300">
                        <p><strong>Created:</strong> {formatTime(task.created_at)}</p>
                        <p><strong>Started:</strong> {formatTime(task.started_at)}</p>
                        <p><strong>Completed:</strong> {formatTime(task.completed_at)}</p>
                        <p><strong>Duration:</strong> {task.execution_time ? `${task.execution_time.toFixed(2)}s` : 'N/A'}</p>
                    </div>
                    <LogsPanel logs={task.logs} exitCode={task.exit_code} />
                </div>
            )}
        </div>
    );
};

export default TaskItem;
