import { useEffect, useRef, useState } from "react";
import { searchAssets, type AssetSearchResult } from "../api/client";

interface SymbolSearchProps {
  onSelect: (symbol: string) => void;
}

export function SymbolSearch({ onSelect }: SymbolSearchProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AssetSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.length < 1) {
      setResults([]);
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const matches = await searchAssets(query);
        setResults(matches);
        setOpen(matches.length > 0);
      } catch {
        setResults([]);
        setOpen(false);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(symbol: string) {
    onSelect(symbol);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="search-wrap" ref={wrapRef}>
      <input
        className="search-input"
        type="text"
        placeholder={loading ? "Searching…" : "Add symbol…"}
        value={query}
        onChange={(e) => setQuery(e.target.value.toUpperCase())}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      {open && (
        <div className="search-results">
          {results.map((asset) => (
            <button
              key={asset.symbol}
              type="button"
              className="search-result"
              onClick={() => handleSelect(asset.symbol)}
            >
              <span className="search-result-symbol">{asset.symbol}</span>
              <span className="search-result-name">{asset.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
