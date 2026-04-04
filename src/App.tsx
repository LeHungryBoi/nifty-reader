import { useState, useEffect } from "react";
import "./App.css";

interface ArchiveItem {
  id: string;
  title: string;
  author: string;
  date: string;
  description: string;
  url: string;
}

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
      // Nifty Archives API endpoint with standard Chrome User Agent
      const response = await fetch(`https://search.niftyarchives.org/api/search?q=${encodeURIComponent(searchQuery)}`, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
          "Accept": "application/json, text/plain, */*",
          "Accept-Language": "en-US,en;q=0.9",
          "Referer": "https://search.niftyarchives.org/"
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      } else {
        // Demo fallback data for demonstration
        setResults([
          {
            id: "1",
            title: "Sample Archive Document #1",
            author: "Archive Team",
            date: "2025-01-15",
            description: "Historical document from nifty archives collection",
            url: "https://search.niftyarchives.org/item/1"
          },
          {
            id: "2",
            title: "Sample Archive Document #2",
            author: "Historical Society",
            date: "2024-11-03",
            description: "Preserved document from public archive",
            url: "https://search.niftyarchives.org/item/2"
          }
        ]);
      }
    } catch (error) {
      console.error("Search failed:", error);
      // Fallback demo data
      setResults([
        {
          id: "1",
          title: "Sample Archive Document #1",
          author: "Archive Team",
          date: "2025-01-15",
          description: "Historical document from nifty archives collection",
          url: "https://search.niftyarchives.org/item/1"
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
      const response = await fetch(item.url, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
          "Accept-Language": "en-US,en;q=0.9",
          "Referer": "https://search.niftyarchives.org/"
        }
      });
      if (response.ok) {
        setReaderContent(await response.text());
      } else {
        setReaderContent(`
          <h1>${item.title}</h1>
          <p><strong>Author:</strong> ${item.author}</p>
          <p><strong>Date:</strong> ${item.date}</p>
          <hr />
          <p>${item.description}</p>
          <p>Document content would be displayed here when API is integrated.</p>
        `);
      }
    } catch (error) {
      setReaderContent(`
        <h2>Document Preview</h2>
        <p>This is a preview of the archive document.</p>
        <p>Full content will load when connected to the live archive.</p>
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