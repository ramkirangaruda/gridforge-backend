import React from 'react';

const LogsPanel = ({ logs, exitCode }) => {
    const hasLogs = logs && logs.trim().length > 0;

    return (
        <div className="mt-4 bg-black rounded-md p-4 max-h-80 overflow-y-auto font-mono text-sm">
            {hasLogs ? (
                <pre className="whitespace-pre-wrap break-words">{logs}</pre>
            ) : (
                <p className="text-gray-500">No logs generated yet.</p>
            )}
            {exitCode !== null && (
                <div className={`mt-2 pt-2 border-t border-gray-700 font-semibold ${exitCode === 0 ? 'text-green-500' : 'text-red-500'}`}>
                    Process exited with code: {exitCode}
                </div>
            )}
        </div>
    );
};

export default LogsPanel;
