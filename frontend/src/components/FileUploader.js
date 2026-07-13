import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadProject } from '../api';

const FileUploader = ({ onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [error, setError] = useState(null);

    const onDrop = useCallback((acceptedFiles) => {
        if (acceptedFiles.length > 0) {
            const acceptedFile = acceptedFiles[0];
            if (acceptedFile.name.endsWith('.zip')) {
                setFile(acceptedFile);
                setError(null);
            } else {
                setError('Invalid file type. Please upload a .zip file.');
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
            setError('Please select a file first.');
            return;
        }

        setUploading(true);
        setError(null);
        setProgress(0);

        try {
            const result = await uploadProject(file, (percent) => {
                setProgress(percent);
            });
            onUploadSuccess(result.id);
            setFile(null); // Reset after successful upload
        } catch (err) {
            setError(err.detail || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="bg-gray-800 rounded-lg shadow-xl p-6">
            <h2 className="text-2xl font-semibold mb-4">Submit a Project</h2>

            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-md p-8 text-center cursor-pointer transition-colors
          ${isDragActive ? 'border-cyan-400 bg-gray-700' : 'border-gray-600 hover:border-cyan-500'}`}
            >
                <input {...getInputProps()} />
                {file ? (
                    <p className="text-green-400">{file.name}</p>
                ) : (
                    <p className="text-gray-400">Drag & drop a .zip file here, or click to select</p>
                )}
            </div>

            {error && <p className="text-red-400 mt-2">{error}</p>}

            {uploading && (
                <div className="w-full bg-gray-700 rounded-full h-2.5 mt-4">
                    <div
                        className="bg-cyan-500 h-2.5 rounded-full transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    ></div>
                </div>
            )}

            <button
                onClick={handleSubmit}
                disabled={!file || uploading}
                className="w-full bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-4 rounded-md mt-4
                   disabled:bg-gray-600 disabled:cursor-not-allowed transition-colors"
            >
                {uploading ? `Uploading... ${Math.round(progress)}%` : 'Submit Task'}
            </button>
        </div>
    );
};

export default FileUploader;
