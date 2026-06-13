import { useState } from 'react';
import type { ArticleModel, EvidenceStatus } from '../types/domain';
import { EvidenceBadge } from './EvidenceBadge';

interface FieldRowProps {
  label: string;
  fieldKey: string;
  value: string | string[] | undefined;
  evidenceStatus?: EvidenceStatus;
  isProtectedCore?: boolean;
  editable?: boolean;
  onEvidenceClick?: () => void;
  onEdit?: (fieldKey: string, newValue: string) => void;
}

function FieldRow({
  label, fieldKey, value, evidenceStatus, isProtectedCore,
  editable, onEvidenceClick, onEdit,
}: FieldRowProps) {
  const [editing, setEditing] = useState(false);
  const displayValue = Array.isArray(value) ? value.join(', ') : (value || '');
  const [editValue, setEditValue] = useState(displayValue);
  const isEmpty = !value || (Array.isArray(value) && value.length === 0);

  const handleSave = () => {
    if (onEdit && editValue !== displayValue) {
      onEdit(fieldKey, editValue);
    }
    setEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') { setEditValue(displayValue); setEditing(false); }
  };

  return (
    <div className={`field-row ${isProtectedCore ? 'field-row--core' : ''} ${isEmpty ? 'field-row--empty' : ''}`}>
      <span className="field-label">{label}</span>
      {editing ? (
        <input
          className="field-edit-input"
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={handleSave}
          onKeyDown={handleKeyDown}
          autoFocus
        />
      ) : (
        <span
          className={`field-value ${editable ? 'field-value--editable' : ''}`}
          onClick={editable ? () => { setEditValue(displayValue); setEditing(true); } : undefined}
          title={editable ? 'Click to edit' : undefined}
        >
          {displayValue || '—'}
        </span>
      )}
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
  const [corrections, setCorrections] = useState<Record<string, string>>({});

  const isConfirmed = article.lifecycle_status === 'confirmed';

  const inferStatus = (field: string): EvidenceStatus => {
    if (article.unknowns?.some((u) => u.toLowerCase().includes(field.toLowerCase()))) {
      return 'unknown';
    }
    return 'inference';
  };

  const handleFieldEdit = (fieldKey: string, newValue: string) => {
    setCorrections(prev => ({ ...prev, [fieldKey]: newValue }));
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
    onConfirm(coreItems, corrections);
  };

  const hasCorrections = Object.keys(corrections).length > 0;

  const fields: { label: string; key: string; value: string | string[] | undefined }[] = [
    { label: 'Object', key: 'object_of_inquiry', value: corrections.object_of_inquiry || article.object_of_inquiry },
    { label: 'Problem', key: 'problem_statement', value: corrections.problem_statement || article.problem_statement },
    { label: 'Thesis', key: 'core_claims', value: article.core_claims },
    { label: 'Genre', key: 'genre', value: corrections.genre || article.genre },
    { label: 'Method', key: 'method_description', value: corrections.method_description || article.method_description || article.method_status },
    { label: 'Novelty', key: 'novelty_mode', value: corrections.novelty_mode || article.novelty_mode },
    { label: 'Discipline', key: 'disciplinary_register_current', value: article.disciplinary_register_current },
  ];

  return (
    <div className="article-card">
      <div className="article-card-header">
        <h2 className="article-title">{corrections.title || article.title || 'Untitled'}</h2>
        <span className={`lifecycle-badge lifecycle-${article.lifecycle_status}`}>
          {article.lifecycle_status}
        </span>
      </div>

      {hasCorrections && !isConfirmed && (
        <div className="corrections-banner" role="status">
          {Object.keys(corrections).length} field(s) edited. Confirm to save.
        </div>
      )}

      <div className="article-fields">
        {fields.map(f => (
          <FieldRow
            key={f.key}
            label={f.label}
            fieldKey={f.key}
            value={f.value}
            evidenceStatus={inferStatus(f.key)}
            editable={!isConfirmed}
            onEdit={handleFieldEdit}
            onEvidenceClick={() => onEvidenceClick('ArticleModel', f.key)}
          />
        ))}
      </div>

      {/* Protected Core Zone */}
      <div className="protected-core-zone">
        <div className="core-header">
          <h3>Protected Core</h3>
          {!isConfirmed && (
            <button
              className="btn btn-small"
              onClick={() => setEditingCore(!editingCore)}
            >
              {editingCore ? 'Done' : 'Edit'}
            </button>
          )}
        </div>
        <p className="core-description">
          Elements that cannot be destroyed for venue fit. Confirm or edit before proceeding.
        </p>
        <ul className="core-list">
          {coreItems.map((item, i) => (
            <li key={i} className="core-item">
              <span className="core-marker">&#9632;</span>
              <span>{item}</span>
              {editingCore && (
                <button
                  className="core-remove"
                  onClick={() => handleRemoveCore(i)}
                  aria-label={`Remove "${item}" from protected core`}
                >
                  &times;
                </button>
              )}
            </li>
          ))}
          {coreItems.length === 0 && (
            <li className="core-item core-item--empty">No protected core elements defined</li>
          )}
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
            {hasCorrections ? 'Confirm with Corrections' : 'Confirm Article Model'}
          </button>
        )}
      </div>
    </div>
  );
}
