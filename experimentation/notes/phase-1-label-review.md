# Phase 1 ? evaluation set and label review

## Dataset

The versioned draft is [`../evaluation/questions-v1.json`](../evaluation/questions-v1.json). It contains 25 standalone questions grounded in the Phase 0 fixed transcript. Each evidence span carries the supplied time interval, transcript excerpt, and original caption `segment_index` references. The JSON records SHA-256 hashes for both the raw caption snapshot and validated segment file so labels can be tied to the exact inputs. Generated chunk IDs are not used.

## Review outcome

All supplied answerable excerpts and time windows were checked against the local validated caption transcript. Stable source segment IDs were filled by timestamp overlap. The set contains 21 answerable, 3 unanswerable, and 1 ambiguous question. The 3 unanswerable cases have null reference answers and no evidence spans. q13 remains ambiguous because the instructor does not identify whether the demonstrated thermistor is NTC or PTC.

q17 was changed from ambiguous to answerable: the explanation distinguishes pins that are permanently connected internally from the switch connection made on pressing, and describes current passing through the diagonal pairing via those connections. q24's reference answer was aligned to the transcript's spoken account: it says the display is off for about 955 ms after 5 ms on, then gives 200 repetitions of 5 ms as one second. The 955 ms figure does not arithmetically equal one second minus 5 ms; this is preserved as a transcript inconsistency, not silently corrected in the label.

## Label and scoring rules

- `segment_index` is the original caption record index, including gaps where marker-only captions were removed; it is the stable evidence unit.
- Each provided answerable span is a source time interval, not a generated chunk. For each chunking configuration, map its chunks to these source IDs/time intervals independently.
- Multiple evidence spans on one question are alternatives or jointly relevant support as described by the question; retain all spans.
- Score Hit@k, Recall@k, and MRR only on answerable questions. q13 is excluded from scored metrics until adjudicated. Unanswerable questions are reported separately and are not retrieval misses.
- Treat timestamps as seconds. A retrieved chunk overlaps a span when `chunk.start_sec <= span.end_sec` and `chunk.end_sec >= span.start_sec` (inclusive boundaries). Report localization at the span level; do not apply an unstated tolerance.
- The label set is a small, hand-authored evaluation sample. It supports controlled comparison on this video only, not statistical significance or broad generalization.

## Review limitation

Caption text is auto-generated and contains transcription errors. Review verifies claims against this fixed transcript, not against independent frame/audio inspection of the entire video. Items whose answers depend on visual details or potentially garbled caption wording should receive extra human review before final scoring. In particular, q08, q12, and q19 concern visual characteristics as described by the instructor; their labels reflect his spoken descriptions.
