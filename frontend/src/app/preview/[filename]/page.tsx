'use client';

import { useState, useEffect } from 'react';
import { use } from 'react';
import Link from 'next/link';

interface PreviewProps {
  params: Promise<{ filename: string }>;
}

export default function Preview({ params }: PreviewProps) {
  const { filename } = use(params);
  const [html, setHtml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedHtml, setEditedHtml] = useState<string | null>(null);

  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const response = await fetch(`http://localhost:8000/preview/${filename}`);
        if (!response.ok) {
          throw new Error('Failed to fetch preview');
        }
        const data = await response.json();
        setHtml(data.html);
        setEditedHtml(data.html);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchPreview();
  }, [filename]);

  const handleCopy = () => {
    if (html) {
      navigator.clipboard.writeText(html);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleSave = () => {
    if (editedHtml) {
      setHtml(editedHtml);
      setIsEditing(false);
    }
  };

  return (
    <div className="min-h-screen p-8">
      <main className="mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Preview Clone</h1>
          <div className="flex gap-4">
            <Link 
              href="/history"
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
            >
              Back to History
            </Link>
            <Link 
              href="/"
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              Back to Cloner
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-8 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : html ? (
          <div
            className="border rounded-lg p-4 flex flex-col items-center mx-auto"
            style={{
              background: '#18181b',
              width: '80vw',
              height: '75vh',
              maxWidth: '1200px',
              maxHeight: '800px',
              boxSizing: 'border-box',
              justifyContent: 'center',
            }}
          >
            <h2 className="text-xl font-semibold mb-4 text-white">
              {isEditing ? 'Edit HTML' : 'Preview'}
            </h2>
            <div className="flex gap-4 mb-4">
              {!isEditing ? (
                <>
                  <button
                    onClick={handleCopy}
                    className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    Copy HTML
                  </button>
                  <button
                    onClick={handleEdit}
                    className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
                  >
                    Edit HTML
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleSave}
                    className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                  >
                    Save Changes
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                  >
                    Cancel
                  </button>
                </>
              )}
            </div>
            {isEditing ? (
              <textarea
                value={editedHtml || ''}
                onChange={(e) => setEditedHtml(e.target.value)}
                className="w-full h-full p-4 font-mono text-sm bg-gray-900 text-white rounded-lg"
                style={{
                  resize: 'none',
                  outline: 'none',
                }}
              />
            ) : (
              <iframe
                srcDoc={html}
                title="Cloned Website Preview"
                style={{
                  width: '100%',
                  height: '100%',
                  background: 'white',
                  borderRadius: '8px',
                  boxShadow: '0 2px 16px rgba(0,0,0,0.2)',
                  border: 'none',
                }}
                sandbox="allow-scripts allow-same-origin"
              />
            )}
          </div>
        ) : (
          <div className="text-center p-8 bg-gray-50 rounded-lg">
            <p className="text-gray-600">No preview available.</p>
          </div>
        )}
      </main>
    </div>
  );
} 