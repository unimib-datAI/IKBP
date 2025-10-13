import axios from "axios";

const endpoint = process.env.ANONYMIZATION_ENDPOINT || "http://0.0.0.0:8081";

async function makeEncryptionRequest(valueToEncrypt) {
    try {
        const res = await axios({
            method: "post",
            url: `${endpoint}/transit/encrypt`,
            headers: {
                "Content-Type": "application/json",
            },
            data: {
                fieldToEncrypt: valueToEncrypt,
            },
        });
        return res.data;
    } catch (error) {
        console.error("Error encrypting value:", valueToEncrypt, error);
        return {
            fieldToEncrypt: valueToEncrypt,
            vaultKey: null,
            error: error.message || error.toString(),
        };
    }
}

async function makeDecryptionRequest(valueToDecrypt) {
    try {
        const res = await axios({
            method: "post",
            url: `${endpoint}/transit/decrypt`,
            headers: {
                "Content-Type": "application/json",
            },
            data: {
                fieldToDecrypt: valueToDecrypt,
            },
        });
        return res.data;
    } catch (error) {
        console.error("Error decrypting value:", valueToDecrypt, error);
        return {
            fieldToDecrypt: valueToDecrypt,
            decryptedData: null,
            error: error.message || error.toString(),
        };
    }
}

/**
 * Extract the annotation text from a document text using inclusive end index.
 * Returns UNKNOWN_ANNOTATION_TEXT if indexes out of range.
 */
function getAnnotationDisplayText(annotationStart, annotationEnd, text) {
    // annotationEnd is inclusive; slice end is exclusive so we add +1
    if (
        Number.isInteger(annotationStart) &&
        Number.isInteger(annotationEnd) &&
        annotationStart >= 0 &&
        annotationEnd >= annotationStart &&
        annotationEnd < text.length
    ) {
        return text.slice(annotationStart, annotationEnd + 1);
    } else {
        return "UNKNOWN_ANNOTATION_TEXT";
    }
}

/**
 * Replace a substring defined by inclusive `end` index.
 */
function replaceSubstring(str, start, end, replacement) {
    const before = str.substring(0, start);
    const after = str.substring(end + 1);
    return before + replacement + after;
}

/**
 * Decode (de-anonymize) a document in-place and return it.
 * - Handles inclusive `end` indexes.
 * - Decrypts using API.
 * - Adjusts subsequent annotations correctly (off-by-one fixes included).
 */
export async function decode(doc) {
    if (!doc || typeof doc !== "object") {
        throw new TypeError("decode: doc must be an object");
    }

    if (
        !(
            doc.annotation_sets &&
            doc.features?.clusters &&
            typeof doc.text === "string"
        )
    ) {
        // Nothing to do, return doc unchanged (but still mark if name present)
        if (typeof doc.name === "string") doc.name += "_ANNOTATED";
        return doc;
    }

    for (const annsetName of Object.keys(doc.annotation_sets)) {
        const anns = doc.annotation_sets[annsetName].annotations ?? [];
        // Walk annotations by index so we can update subsequent annotations safely
        for (let i = 0; i < anns.length; i++) {
            const annotation = anns[i];
            if (
                !Number.isInteger(annotation.start) ||
                !Number.isInteger(annotation.end) ||
                annotation.start < 0 ||
                annotation.end < annotation.start
            ) {
                // skip malformed annotation
                continue;
            }

            const extracted = getAnnotationDisplayText(
                annotation.start,
                annotation.end,
                doc.text,
            );

            const encryptionKey = annotation.encryptionKey;
            const result = encryptionKey
                ? await makeDecryptionRequest(encryptionKey)
                : null;
            const deAnonymized = result?.decryptedData;
            console.log(
                "*** De Anonimized ***",
                deAnonymized,
                extracted,
                `docId=${doc.id ?? "unknown"}`,
            );

            if (typeof deAnonymized !== "string") {
                // Log detailed diagnostic information
                console.error(
                    `Error decrypting encryptionKey. annset=${annsetName} index=${i} start=${annotation.start} end=${annotation.end} extracted='${extracted}' docId=${doc.id ?? "unknown"}`,
                );
                // Skip replacement; do not mutate doc.text or annotation indexes for this entry.
                continue;
            }

            const originalStart = annotation.start;
            const originalEnd = annotation.end; // inclusive
            const oldLen = originalEnd - originalStart + 1;
            const newLen = deAnonymized.length;
            const delta = newLen - oldLen;

            // Replace the substring in the document text
            doc.text = replaceSubstring(
                doc.text,
                originalStart,
                originalEnd,
                deAnonymized,
            );

            // Update the current annotation. Because `end` is inclusive:
            annotation.end = originalStart + newLen;

            // If length changed, shift later annotations that come after the originalEnd.
            if (delta !== 0) {
                for (let j = i + 1; j < anns.length; j++) {
                    const other = anns[j];
                    if (
                        !Number.isInteger(other.start) ||
                        !Number.isInteger(other.end)
                    )
                        continue;

                    // If other annotation starts strictly after the original annotation's originalEnd
                    // it should be shifted by delta. If it overlaps, we log and skip.
                    if (other.start > originalEnd) {
                        other.start += delta;
                        other.end += delta;
                    } else if (
                        other.start <= originalEnd &&
                        other.end > originalEnd
                    ) {
                        console.warn(
                            `Overlapping annotation detected in set ${annsetName} at index ${j}; manual handling required.`,
                        );
                    }
                    // If `other` is fully inside the replaced span (other.end <= originalEnd),
                    // it refers to content that was replaced; this is ambiguous and left unchanged.
                }
            }
        }
    }

    if (typeof doc.name === "string") {
        doc.name += "_ANNOTATED";
    } else {
        doc.name = (doc.name ?? "") + "_ANNOTATED";
    }
    doc.features.anonymized = false;
    return doc;
}
