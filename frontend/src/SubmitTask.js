import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion } from "framer-motion";
import { uploadProject } from "./api";

const SubmitTask = ({ onTaskSubmitted }) => {
    const [file, setFile] = useState(null);
    const [error, setError] = useState("");
    const [isUploading, setIsUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);

    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) {
            const acceptedFile = acceptedFiles[0];
            if (acceptedFile.name.endsWith('.zip')) {
                setFile(acceptedFile);
                setError("");
            } else {
                setError("Invalid file type. Please upload a .zip file.");
                setFile(null);
            }
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/zip': ['.zip'] },
        multiple: false,
    });

    const handleSubmit = async () => {
        if (!file) {
            setError("Please select a file to upload.");
            return;
        }
        setIsUploading(true);
        setError("");
        setUploadProgress(0);
        try {
            const newTask = await uploadProject(file, (progress) => {
                setUploadProgress(progress);
            });
            onTaskSubmitted(newTask); // Notify parent component
            setFile(null); // Reset file input
        } catch (err) {
            setError(err.message || "An unknown error occurred during upload.");
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl shadow-lg p-6 border border-gray-700">
            <h2 className="text-2xl font-bold mb-4 text-cyan-300">Submit New Project</h2>

            <div
                {...getRootProps()}
                className={`w-full p-8 border-2 border-dashed rounded-lg cursor-pointer text-center transition-colors duration-300
                    ${isDragActive ? "border-cyan-400 bg-cyan-500/10" : "border-gray-600 hover:border-gray-500"}
                `}
            >
                <input {...getInputProps()} />
                {file ? (
                    <p className="text-green-400">{file.name}</p>
                ) : isDragActive ? (
                    <p>Drop the .zip file here...</p>
                ) : (
                    <p>Drag & drop a .zip file here, or click to select</p>
                )}
            </div>

            {error && <p className="text-red-400 mt-2 text-sm">{error}</p>}

            {isUploading && (
                <div className="w-full bg-gray-700 rounded-full h-2.5 mt-4">
                    <div
                        className="bg-cyan-500 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                    ></div>
                </div>
            )}

            <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.95 }}
                className="w-full bg-cyan-500 text-white font-bold py-3 rounded-lg hover:bg-cyan-600 transition-colors duration-300 shadow-lg mt-4 disabled:bg-gray-500 disabled:cursor-not-allowed"
                onClick={handleSubmit}
                disabled={!file || isUploading}
            >
                {isUploading ? `Uploading... ${Math.round(uploadProgress)}%` : "Run Project"}
            </motion.button>
        </div>
    );
};

export default SubmitTask;