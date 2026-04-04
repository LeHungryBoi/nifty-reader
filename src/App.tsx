import { useState, useEffect } from "react";
import "./App.css";

import { fetchSearchResults, fetchAndCleanStory, ArchiveItem } from "./services/nifty";

function App() {
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<ArchiveItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<ArchiveItem | null>(null);
  const [readerContent, setReaderContent] = useState("");

  const searchArchives = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    try {
      // Use the nifty service to fetch/parse search
      const data = await fetchSearchResults(searchQuery);
      setResults(data);
    } catch (error) {
      console.error("Search failed:", error);
      // Fallback for demonstration if CORS/fetch fails
      setResults([
        {
          id: "1",
          title: "Demo Story (Search failed, see console)",
          author: "Self",
          date: "2025-01-15",
          description: "Search likely failed due to CORS. In a real Tauri app, use the http plugin.",
          url: "https://www.nifty.org/nifty/lesbian/hookers/linda-becomes-a-prostitute"
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const openReader = async (item: ArchiveItem) => {
    setSelectedItem(item);
    setLoading(true);
    
    try {
      // Fetch and clean content using the service
      const cleaned = await fetchAndCleanStory(item.url);
      setReaderContent(cleaned);
    } catch (error) {
      setReaderContent(`
        <div class="error">
          <h2>Could not load story</h2>
          <p>This may be due to CORS restrictions or a network error.</p>
          <p>Visit the story directly at: <a href="${item.url}" target="_blank">${item.url}</a></p>
        </div>
      `);
    } finally {
      setLoading(false);
    }
  };

  const closeReader = () => {
    setSelectedItem(null);
    setReaderContent("");
  };

  useEffect(() => {
    // Enable keyboard shortcuts
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeReader();
      if (e.key === "Enter" && !selectedItem) searchArchives();
    };
    
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedItem]);

  return (
    <div className="app">
      <header className="header">
        <h1>📚 Nifty Reader</h1>
        <p>Desktop reader for Nifty Archives</p>
      </header>

      {!selectedItem ? (
        <>
          <div className="search-bar">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search archives..."
              className="search-input"
            />
            <button onClick={searchArchives} disabled={loading} className="search-button">
              {loading ? "Searching..." : "Search"}
            </button>
          </div>

          <div className="results">
            {results.length > 0 && (
              <h3>Found {results.length} results</h3>
            )}
            
            {results.map((item) => (
              <div key={item.id} className="result-item" onClick={() => openReader(item)}>
                <h4>{item.title}</h4>
                <div className="meta">
                  <span>{item.author}</span>
                  <span>{item.date}</span>
                </div>
                <p>{item.description}</p>
              </div>
            ))}

            {results.length === 0 && !loading && (
              <div className="empty-state">
                <h3>Welcome to Nifty Reader</h3>
                <p>Search for documents in the Nifty Archives database</p>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="reader">
          <div className="reader-header">
            <button onClick={closeReader} className="back-button">← Back</button>
            <h2>{selectedItem.title}</h2>
          </div>
          
          {loading ? (
            <div className="loading">Loading document...</div>
          ) : (
            <div className="reader-content" dangerouslySetInnerHTML={{ __html: readerContent }} />
          )}
        </div>
      )}

      <footer className="footer">
        <p>Nifty Reader • Built with Tauri + React</p>
      </footer>
    </div>
  );
}

export default App;