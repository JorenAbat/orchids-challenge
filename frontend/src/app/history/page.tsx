'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface CloneHistory {
  id: string;
  url: string;
  timestamp: string;
  filename: string;
}

export default function History() {
  const [history, setHistory] = useState<CloneHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch('http://localhost:8000/history');
        if (!response.ok) {
          throw new Error('Failed to fetch history');
        }
        const data = await response.json();
        setHistory(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  return (
    <div className="min-h-screen p-8">
      <main className="mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Clone History</h1>
          <Link 
            href="/"
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600"
          >
            Back to Cloner
          </Link>
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
        ) : history.length === 0 ? (
          <div className="text-center p-8 bg-gray-50 rounded-lg">
            <p className="text-gray-600">No clones in history yet.</p>
          </div>
        ) : (
          <div className="max-w-2xl mx-auto">
            <div className="space-y-4">
              {history.map((item) => (
                <div 
                  key={item.id}
                  className="p-4 bg-white rounded-lg shadow hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-lg text-black">{item.url}</h3>
                      <p className="text-sm text-gray-500">
                        Cloned on {new Date(item.timestamp).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Link
                        href={`/preview/${item.filename}`}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                      >
                        View
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
} 