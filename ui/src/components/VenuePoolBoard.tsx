import { useState } from 'react';
import type { VenueCandidate } from '../types/domain';
import { VenueCandidateCard } from './VenueCandidateCard';

interface Props {
  candidates: VenueCandidate[];
  onSelectVenue: (venueId: string) => void;
  onDiscover?: () => void;
  isLoading?: boolean;
  poolStatus?: string;
}

type SortKey = 'confidence' | 'name' | 'status';

const CONFIDENCE_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

export function VenuePoolBoard({
  candidates,
  onSelectVenue,
  onDiscover,
  isLoading,
  poolStatus,
}: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<SortKey>('confidence');

  const sorted = [...candidates].sort((a, b) => {
    if (sortBy === 'confidence') {
      return (CONFIDENCE_ORDER[a.confidence] ?? 9) - (CONFIDENCE_ORDER[b.confidence] ?? 9);
    }
    if (sortBy === 'name') {
      return a.canonical_name.localeCompare(b.canonical_name);
    }
    return a.status.localeCompare(b.status);
  });

  const handleSelect = (id: string) => {
    setSelectedId(id);
  };

  const handleConfirmSelection = () => {
    if (selectedId) {
      onSelectVenue(selectedId);
    }
  };

  if (candidates.length === 0) {
    return (
      <div className="venue-pool-empty">
        <h2>Пул журналов</h2>
        <p>Кандидаты площадок ещё не найдены.</p>
        {poolStatus === 'no_pathways' && (
          <p className="pool-hint">Сначала постройте дисциплинарные пути для поиска площадок.</p>
        )}
        {onDiscover && (
          <button
            className="btn btn-primary"
            onClick={onDiscover}
            disabled={isLoading}
          >
            {isLoading ? 'Поиск…' : 'Найти площадки'}
          </button>
        )}
      </div>
    );
  }

  const highCount = candidates.filter(c => c.confidence === 'high').length;
  const mediumCount = candidates.filter(c => c.confidence === 'medium').length;

  return (
    <div className="venue-pool-board">
      <div className="pool-header">
        <div className="pool-header-left">
          <h2>Пул журналов</h2>
          <div className="pool-summary">
            <span className="pool-total">{candidates.length} кандидатов</span>
            {highCount > 0 && <span className="pool-badge conf-high">{highCount} высок.</span>}
            {mediumCount > 0 && <span className="pool-badge conf-medium">{mediumCount} средн.</span>}
          </div>
        </div>
        <div className="pool-controls">
          <label className="sort-label" htmlFor="pool-sort">Сортировка:</label>
          <select
            id="pool-sort"
            className="pool-sort-select"
            value={sortBy}
            onChange={e => setSortBy(e.target.value as SortKey)}
          >
            <option value="confidence">Уверенность</option>
            <option value="name">Название</option>
            <option value="status">Статус</option>
          </select>
          {onDiscover && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={onDiscover}
              disabled={isLoading}
            >
              Повторный поиск
            </button>
          )}
        </div>
      </div>

      <div className="pool-grid">
        {sorted.map(c => (
          <VenueCandidateCard
            key={c.venue_candidate_id}
            candidate={c}
            isSelected={selectedId === c.venue_candidate_id}
            onSelect={handleSelect}
          />
        ))}
      </div>

      {selectedId && (
        <div className="pool-action-bar">
          <span className="pool-action-label">
            Выбрано: {candidates.find(c => c.venue_candidate_id === selectedId)?.canonical_name}
          </span>
          <button
            className="btn btn-primary"
            onClick={handleConfirmSelection}
            disabled={isLoading}
          >
            Выбрать для оценки соответствия
          </button>
        </div>
      )}
    </div>
  );
}
