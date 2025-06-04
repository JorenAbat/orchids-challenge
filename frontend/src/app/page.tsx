// Required for React hooks and browser functionality
'use client';

// Import useState for managing component state
import { useState } from 'react';
import Link from 'next/link';

// Helper to extract domain from URL
function getDomain(url: string) {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

interface CloneMetadata {
  id: string;
  url: string;
  timestamp: string;
  filename: string;
}

// Main component for the website cloning interface
export default function Home() {
  // State management for the component:
  // url: stores the target website URL
  // loading: tracks the cloning process status
  // preview: stores the generated HTML
  // error: stores any error messages
  // isEditing: tracks whether we're in edit mode
  // metadata: stores the clone metadata
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedHtml, setEditedHtml] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<CloneMetadata | null>(null);

  // Handles form submission when user requests website cloning
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    // Sanitize input URL (basic check)
    if (!/^https?:\/\//.test(url)) {
      setError('Please enter a valid http or https URL.');
      return;
    }
    setLoading(true);
    setError(null);
    setPreview(null);
    setMetadata(null);
    try {
      const response = await fetch('http://localhost:8000/clone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });
      if (!response.ok) {
        throw new Error('Failed to clone website');
      }
      const data = await response.json();
      setPreview(data.html);
      setMetadata(data.metadata);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  // Copy HTML to clipboard
  const handleCopy = () => {
    if (preview) {
      navigator.clipboard.writeText(preview);
    }
  };

  // Reset preview and input
  const handleReset = () => {
    setUrl('');
    setPreview(null);
    setError(null);
    setMetadata(null);
  };

  // Handle HTML editing
  const handleEdit = () => {
    setIsEditing(true);
    setEditedHtml(preview);
  };

  // Handle saving edited HTML
  const handleSave = () => {
    if (editedHtml) {
      setPreview(editedHtml);
      setIsEditing(false);
    }
  };

  // Component UI structure
  return (
    // Main container with padding
    <div className="min-h-screen p-8">
      {/* Content wrapper with max width */}
      <main className="mx-auto">
        {/* Application title and navigation */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Website Cloner</h1>
          <Link 
            href="/history"
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            View History
          </Link>
        </div>
        
        {/* URL input form */}
        <form onSubmit={handleSubmit} className="mb-8 flex justify-center">
          {/* Input and button container */}
          <div className="flex gap-4 w-full max-w-xl">
            {/* URL input field */}
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Enter website URL (e.g., https://example.com)"
              className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-md"
              required
            />
            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed"
            >
              {loading ? 'Cloning...' : 'Clone Website'}
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-6 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
            >
              Reset
            </button>
          </div>
        </form>

        {/* Error display section */}
        {error && (
          <div className="mb-8 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        )}

        {/* Preview/Edit section */}
        {preview && (
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
              {isEditing ? 'Edit HTML' : `Preview${url ? ` of ${getDomain(url)} clone` : ''}`}
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
                  {metadata && (
                    <Link
                      href={`/preview/${metadata.filename}`}
                      target="_blank"
                      className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      View in History
                    </Link>
                  )}
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
            {/* Show loading spinner inside preview box if loading */}
            {loading ? (
              <div className="flex justify-center items-center h-full w-full">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
              </div>
            ) : isEditing ? (
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
                srcDoc={preview}
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
        )}
      </main>
    </div>
  );
}
