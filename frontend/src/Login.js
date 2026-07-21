import React, { useState } from "react";
import { motion } from "framer-motion";
import { login } from "./api";

const Login = ({ notice, onLoginSuccess, onSwitchToRegister }) => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!username || !password) {
            setError("Please enter your username and password.");
            return;
        }

        setIsSubmitting(true);
        setError("");
        try {
            await login(username, password);
            onLoginSuccess();
        } catch (err) {
            // login() tags thrown errors with `.status` (see api/index.js)
            // specifically so this can tell "wrong password" apart from
            // "the server's having issues" apart from "can't reach the
            // server at all" - a bare Error message alone can't carry
            // that distinction.
            if (err.status === 401) {
                setError("Incorrect username or password.");
            } else if (err.status === 429) {
                setError("Too many attempts. Please wait a minute and try again.");
            } else if (!err.status) {
                setError("Can't reach the server. Check your connection and try again.");
            } else {
                setError(err.message || "Something went wrong. Please try again.");
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="max-w-md mx-auto bg-gray-800/50 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-gray-700">
            <h2 className="text-2xl font-bold mb-4 text-cyan-300">Log In</h2>

            {notice && <p className="text-green-400 mb-4 text-sm">{notice}</p>}

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="login-username" className="block text-sm text-gray-400 mb-1">
                        Username
                    </label>
                    <input
                        id="login-username"
                        type="text"
                        autoComplete="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                    />
                </div>
                <div>
                    <label htmlFor="login-password" className="block text-sm text-gray-400 mb-1">
                        Password
                    </label>
                    <input
                        id="login-password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                    />
                </div>

                {error && <p className="text-red-400 text-sm">{error}</p>}

                <motion.button
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.95 }}
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full bg-cyan-500 text-white font-bold py-3 rounded-lg hover:bg-cyan-600 transition-colors duration-300 shadow-lg disabled:bg-gray-500 disabled:cursor-not-allowed"
                >
                    {isSubmitting ? "Logging in..." : "Log In"}
                </motion.button>
            </form>

            <p className="text-sm text-gray-400 mt-4 text-center">
                Don't have an account?{" "}
                <button
                    type="button"
                    onClick={onSwitchToRegister}
                    className="text-cyan-400 hover:text-cyan-300 underline"
                >
                    Register
                </button>
            </p>
        </div>
    );
};

export default Login;
