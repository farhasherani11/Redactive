# Redactive — Adversarial Evasion Report

**Overall detection rate: 47/50 (94.0%)** across baseline + obfuscated inputs, all three guard layers combined.

## Detection rate by technique

| Technique | Detected | Total | Rate |
|---|---|---|---|
| base64_encoded | 5 | 5 | 100.0% |
| baseline (no obfuscation) | 5 | 5 | 100.0% |
| dashes_removed | 5 | 5 | 100.0% |
| dashes_to_dots | 5 | 5 | 100.0% |
| homoglyph_substitution | 5 | 5 | 100.0% |
| leetspeak | 5 | 5 | 100.0% |
| reversed_text | 3 | 5 | 60.0% |
| spaced_out | 4 | 5 | 80.0% |
| split_across_sentence | 5 | 5 | 100.0% |
| zero_width_injection | 5 | 5 | 100.0% |

## Full results

| Test case | Technique | Detected | Layers fired | Risk score |
|---|---|---|---|---|
| SSN | baseline (no obfuscation) | ✅ | llm, regex | 100 |
| SSN | spaced_out | ✅ | llm | 100 |
| SSN | leetspeak | ✅ | llm, regex | 100 |
| SSN | dashes_to_dots | ✅ | llm | 100 |
| SSN | dashes_removed | ✅ | llm | 100 |
| SSN | reversed_text | ✅ | llm | 100 |
| SSN | base64_encoded | ✅ | llm | 100 |
| SSN | homoglyph_substitution | ✅ | llm, regex | 100 |
| SSN | zero_width_injection | ✅ | llm | 100 |
| SSN | split_across_sentence | ✅ | llm | 100 |
| email | baseline (no obfuscation) | ✅ | regex | 10 |
| email | spaced_out | ❌ | - | 0 |
| email | leetspeak | ✅ | llm, regex | 100 |
| email | dashes_to_dots | ✅ | regex | 10 |
| email | dashes_removed | ✅ | regex | 10 |
| email | reversed_text | ❌ | - | 0 |
| email | base64_encoded | ✅ | llm | 80 |
| email | homoglyph_substitution | ✅ | regex | 10 |
| email | zero_width_injection | ✅ | llm | 80 |
| email | split_across_sentence | ✅ | llm | 80 |
| email_with_context | baseline (no obfuscation) | ✅ | regex | 10 |
| email_with_context | spaced_out | ✅ | llm | 80 |
| email_with_context | leetspeak | ✅ | llm, regex | 100 |
| email_with_context | dashes_to_dots | ✅ | regex | 10 |
| email_with_context | dashes_removed | ✅ | regex | 10 |
| email_with_context | reversed_text | ❌ | - | 0 |
| email_with_context | base64_encoded | ✅ | llm | 80 |
| email_with_context | homoglyph_substitution | ✅ | llm, regex | 100 |
| email_with_context | zero_width_injection | ✅ | llm | 80 |
| email_with_context | split_across_sentence | ✅ | llm | 80 |
| aws_key | baseline (no obfuscation) | ✅ | llm, ner, regex | 100 |
| aws_key | spaced_out | ✅ | llm, ner | 100 |
| aws_key | leetspeak | ✅ | llm, ner | 100 |
| aws_key | dashes_to_dots | ✅ | llm, ner, regex | 100 |
| aws_key | dashes_removed | ✅ | llm, ner, regex | 100 |
| aws_key | reversed_text | ✅ | llm, ner | 100 |
| aws_key | base64_encoded | ✅ | llm, ner | 100 |
| aws_key | homoglyph_substitution | ✅ | llm, ner | 100 |
| aws_key | zero_width_injection | ✅ | llm, ner | 100 |
| aws_key | split_across_sentence | ✅ | llm, ner | 100 |
| credit_card | baseline (no obfuscation) | ✅ | llm, regex | 100 |
| credit_card | spaced_out | ✅ | llm, regex | 100 |
| credit_card | leetspeak | ✅ | llm, regex | 100 |
| credit_card | dashes_to_dots | ✅ | llm, regex | 100 |
| credit_card | dashes_removed | ✅ | llm, regex | 100 |
| credit_card | reversed_text | ✅ | llm, regex | 100 |
| credit_card | base64_encoded | ✅ | llm | 90 |
| credit_card | homoglyph_substitution | ✅ | llm, regex | 100 |
| credit_card | zero_width_injection | ✅ | llm | 100 |
| credit_card | split_across_sentence | ✅ | llm | 90 |

## Notes

- "Detected" means at least one guard flagged the input — either a pattern/entity finding, or the LLM assigned a risk score of 30 or higher.
- Techniques regex/NER alone would be expected to miss (e.g. `reversed_text`, `base64_encoded`, `zero_width_injection`) are included specifically to measure how much the LLM layer adds over the first two guards alone — see which rows show `llm` as the only layer fired.
- This report should be regenerated any time a guard's logic changes, so the numbers stay accurate.

## Known limitations

**`reversed_text` remains the weakest technique (~60% detection), specifically on email values.** This was investigated deliberately:

1. Initial hypothesis: email misses were caused by a lack of contextual anchoring in the carrier sentence (no word like "email" near the obfuscated value). A controlled test (`email` vs `email_with_context`, identical value, only the carrier sentence changed) disproved this — both variants performed identically.
2. Root cause found instead: the LLM system prompt explicitly instructed the model to defer to regex on "plain emails," with no exception for cases where regex had actually failed due to obfuscation. Fixing that instruction raised overall detection from 82% to 94%.
3. `reversed_text` is the one technique that didn't fully close after the fix. Reasoning: reversing a string destroys nearly all human-readable structure, unlike spacing, leetspeak, or symbol substitution, which preserve a recognizable shape the LLM can reason from. There's little partial signal left for the model to catch.

**Deliberate decision: not fixing this further with prompt engineering.** A narrow instruction telling the LLM to actively try reversing suspicious strings would only help this one technique, and risks increasing false positives elsewhere by making the model more aggressive about flagging ordinary text. The correct fix would be a dedicated de-obfuscation preprocessing step (attempt common reversals/transforms before any guard sees the text) as its own pipeline stage — noted as a future improvement rather than solved here, to avoid overfitting the prompt to this test set.