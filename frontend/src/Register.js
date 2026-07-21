import React, { useState } from "react";
import { motion } from "framer-motion";
import { register } from "./api";

const Register = ({ onRegisterSuccess, onSwitchToLogin }) => {
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Mirrors backend/api/models.py's UserCreate constraints, to catch
        // the common case before a round trip - not a substitute for the
        // server's own validation, which still runs regardless and is
        // still handled below (the err.status === 422 branch).
        if (username.length < 3 || username.length > 64) {
            setError("Username must be between 3 and 64 characters.");
            return;
        }
        if (password.length < 8 || password.length > 72) {
            setError("Password must be between 8 and 72 characters.");
            return;
        }
        if (password !== confirmPassword) {
            setError("Passwords don't match.");
            return;
        }

        setIsSubmitting(true);
        setError("");
        try {
            await register(username, password);
            onRegisterSuccess();
        } catch (err) {
            if (err.status === 400) {
                setError(err.message); // e.g. "Username already exists."
            } else if (err.status === 422) {
                setError(err.message); // pydantic validation, already a real message via extractErrorMessage()
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
            <h2 className="text-2xl font-bold mb-4 text-cyan-300">Create an Account</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="register-username" className="block text-sm text-gray-400 mb-1">
                        Username
                    </label>
                    <input
                        id="register-username"
                        type="text"
                        autoComplete="username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                    />
                    <p className="text-xs text-gray-500 mt-1">3-64 characters.</p>
                </div>
                <div>
                    <label htmlFor="register-password" className="block text-sm text-gray-400 mb-1">
                        Password
                    </label>
                    <input
                        id="register-password"
                        type="password"
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-cyan-400"
                    />
                    <p className="text-xs text-gray-500 mt-1">8-72 characters.</p>
                </div>
                <div>
                    <label htmlFor="register-confirm-password" className="block text-sm text-gray-400 mb-1">
                        Confirm Password
                    </label>
                    <input
                        id="register-confirm-password"
                        type="password"
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
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
                    {isSubmitting ? "Creating account..." : "Register"}
                </motion.button>
            </form>

            <p className="text-sm text-gray-400 mt-4 text-center">
                Already have an account?{" "}
                <button
                    type="button"
                    onClick={onSwitchToLogin}
                    className="text-cyan-400 hover:text-cyan-300 underline"
                >
                    Log In
                </button>
            </p>
        </div>
    );
};

export default Register;
