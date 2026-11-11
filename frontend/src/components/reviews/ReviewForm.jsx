import { useState } from 'react';
import { Button } from '../ui/Button';
import { Field } from '../ui/Field';
import { StarInput } from '../ui/StarRating';
import styles from './Reviews.module.css';

const MAX_COMMENT = 2000;

/** Create or edit a review. `onSubmit` receives { rating, comment }. */
export function ReviewForm({ initial, onSubmit, onCancel, submitLabel = 'Publish review' }) {
  const [rating, setRating] = useState(initial?.rating || 0);
  const [comment, setComment] = useState(initial?.comment || '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    if (!rating) return setError('Pick a rating from 1 to 5 stars.');
    if (comment.length > MAX_COMMENT) return setError(`Keep the review under ${MAX_COMMENT} characters.`);
    setBusy(true);
    const ok = await onSubmit({ rating, comment: comment.trim() });
    setBusy(false);
    if (ok && !initial) {
      setRating(0);
      setComment('');
    }
  };

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <StarInput
        value={rating}
        onChange={(value) => {
          setRating(value);
          setError('');
        }}
        error={error}
      />
      <Field
        as="textarea"
        label="Your thoughts"
        placeholder="What stayed with you? (optional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        hint={<span className="tabular">{comment.length} / {MAX_COMMENT}</span>}
        maxLength={MAX_COMMENT}
      />
      <div className={styles.formActions}>
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        )}
        <Button type="submit" variant="primary" loading={busy}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
