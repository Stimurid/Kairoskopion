import { useState } from 'react';
import type { ArticleModel, EvidenceStatus } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

interface FieldRowProps {
  label: string;
  value: string | string[] | undefined;
  evidenceStatus?: EvidenceStatus;
  isProtectedCore?: boolean;
  onEvidenceClick?: () => void;
}

function FieldRow({ label, value, evidenceStatus, isProtectedCore, onEvidenceClick }: FieldRowProps) {
  const displayValue = Array.isArray(value) ? value.join(', ') : (value || '—');
  const isEmpty = !value || (Array.isArray(value) && value.length === 0);

  return (
    <div className={`field-row ${isProtectedCore ? 'field-row--core' : ''} ${isEmpty ? 'field-row--empty' : ''}`}>
      <span className="field-label">{label}</span>
      <span className="field-value">{displayValue}</span>
      {evidenceStatus && (
        <EvidenceBadge status={evidenceStatus} onClick={onEvidenceClick} />
      )}
    </div>
  );
}

interface Props {
  article: ArticleModel;
  onConfirm: (protectedCore: string[], corrections: Record<string, string>) => void;
  onEvidenceClick: (entityType: string, fieldPath: string) => void;
}

export function ArticleCard({ article, onConfirm, onEvidenceClick }: Props) {
  const [editingCore, setEditingCore] = useState(false);
  const [coreItems, setCoreItems] = useState<string[]>(article.protected_core || []);
  const [newCoreItem, setNewCoreItem] = useState('');

  const isConfirmed = article.lifecycle_status === 'confirmed';

  const inferStatus = (field: string): EvidenceStatus => {
    if (article.unknowns?.some((u) => u.toLowerCase().includes(field.toLowerCase()))) {
      return 'unknown';
    }
    if (article.evidence_refs?.length > 0) return 'inference';
    return 'inference';
  };

  const handleAddCore = () => {
    if (newCoreItem.trim()) {
      setCoreItems([...coreItems, newCoreItem.trim()]);
      setNewCoreItem('');
    }
  };

  const handleRemoveCore = (idx: number) => {
    setCoreItems(coreItems.filter((_, i) => i !== idx));
  };

  const handleConfirm = () => {
    onConfirm(coreItems, {});
  };

  return (
    <div className="article-card">
      <div className="article-card-header">
        <h2 className="article-title">{article.title || 'Untitled'}</h2>
        <span className={`lifecycle-badge lifecycle-${article.lifecycle_status}`}>
          {article.lifecycle_status}
        </span>
      </div>

      <div className="article-fields">
        <FieldRow
          label="Object"
          value={article.object_of_inquiry}
          evidenceStatus={inferStatus('object')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'object_of_inquiry')}
        />
        <FieldRow
          label="Problem"
          value={article.problem_statement}
          evidenceStatus={inferStatus('problem')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'problem_statement')}
        />
        <FieldRow
          label="Thesis"
          value={article.core_claims}
          evidenceStatus={inferStatus('thesis')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'core_claims')}
        />
        <FieldRow
          label="Genre"
          value={article.genre}
          evidenceStatus={inferStatus('genre')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'genre')}
        />
        <FieldRow
          label="Method"
          value={article.method_description || article.method_status}
          evidenceStatus={inferStatus('method')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'method_status')}
        />
        <FieldRow
          label="Novelty"
          value={article.novelty_mode}
          evidenceStatus={inferStatus('novelty')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'novelty_mode')}
        />
        <FieldRow
          label="Discipline"
          value={article.disciplinary_register_current}
          evidenceStatus={inferStatus('discipline')}
          onEvidenceClick={() => onEvidenceClick('ArticleModel', 'disciplinary_register_current')}
        />
      </div>

      {/* Protected Core Zone */}
      <div className="protected-core-zone">
        <div className="core-header">
          <h3>Protected Core</h3>
          <button
            className="btn btn-small"
            onClick={() => setEditingCore(!editingCore)}
          >
            {editingCore ? 'Done' : 'Edit'}
          </button>
        </div>
        <p className="core-description">
          Elements that cannot be destroyed for venue fit. Confirm or edit before proceeding.
        </p>
        <ul className="core-list">
          {coreItems.map((item, i) => (
            <li key={i} className="core-item">
              <span className="core-marker">■</span>
              <span>{item}</span>
              {editingCore && (
                <button
                  className="core-remove"
                  onClick={() => handleRemoveCore(i)}
                  aria-label={`Remove "${item}" from protected core`}
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
        {editingCore && (
          <div className="core-add">
            <input
              type="text"
              value={newCoreItem}
              onChange={(e) => setNewCoreItem(e.target.value)}
              placeholder="Add core element..."
              onKeyDown={(e) => { if (e.key === 'Enter') handleAddCore(); }}
            />
            <button className="btn btn-small" onClick={handleAddCore}>Add</button>
          </div>
        )}
      </div>

      {/* Unknowns */}
      {article.unknowns && article.unknowns.length > 0 && (
        <div className="unknowns-section">
          <h3>Unknowns</h3>
          <ul className="unknowns-list">
            {article.unknowns.map((u, i) => (
              <li key={i}>
                <EvidenceBadge status="unknown" /> {u}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Confidence footer */}
      <div className="article-footer">
        <span className="confidence-label">
          Confidence: <strong>{article.confidence || 'preliminary'}</strong>
        </span>
        <span className="source-count">
          Sources: {article.evidence_refs?.length ?? 0}
        </span>
        {!isConfirmed && (
          <button className="btn btn-primary" onClick={handleConfirm}>
            Confirm Article Model
          </button>
        )}
      </div>
    </div>
  );
}
