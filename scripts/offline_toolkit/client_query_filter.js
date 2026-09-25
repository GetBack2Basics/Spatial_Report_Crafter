/*
 * Generic, dependency-free "WHERE"-style expression matcher for filtering
 * an in-memory array of records in an offline "Map-in-a-Box" report.
 *
 * Schema-free extraction of a pattern used in an offline case study of the
 * Spatial Report Crafter method (see
 * docs/lessons_learned_offline_case_study.md). Contains no project data,
 * field names, or schema.
 *
 * This is a small client-side expression matcher, not a real SQL engine —
 * make that clear in any UI that surfaces it to report readers.
 *
 * Supported syntax: one or more conditions of the form
 *   <field> (= | != | > | >= | < | <= | LIKE) <value>
 * combined with AND / OR (left-to-right, no operator precedence / grouping),
 * with an optional leading "SELECT * FROM x WHERE" or "WHERE" stripped.
 * <value> may be a quoted string ('...' or "..."), or an unquoted number/
 * bareword; LIKE patterns use SQL-style "%" (any run of characters) and "_"
 * (any single character) wildcards, case-insensitively.
 *
 * Usage:
 *   import { compileQuery } from "./client_query_filter.js";
 *   // fieldResolver(record, field) -> value, lets you map query field
 *   // names (case-insensitively) to however your records are shaped,
 *   // including synonyms for well-known derived properties.
 *   const predicate = compileQuery("category = 'x' AND size > 10", (record, field) => {
 *     const key = field.trim().toLowerCase();
 *     if (key === "size") return record.size;
 *     const propKey = Object.keys(record.properties).find(k => k.toLowerCase() === key);
 *     return propKey ? record.properties[propKey] : undefined;
 *   });
 *   const matches = allRecords.filter(record => !predicate || predicate(record));
 */

export function parseValue(raw) {
  const trimmed = raw.trim();
  if ((trimmed.startsWith("'") && trimmed.endsWith("'")) || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
    return trimmed.slice(1, -1);
  }
  const num = Number(trimmed);
  return trimmed !== "" && !Number.isNaN(num) ? num : trimmed;
}

export function likeToRegex(pattern) {
  const escaped = String(pattern)
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/%/g, ".*")
    .replace(/_/g, ".");
  return new RegExp(`^${escaped}$`, "i");
}

function compileCondition(text, fieldResolver) {
  const trimmed = text.trim();
  const match = trimmed.match(/^([A-Za-z0-9_ ]+?)\s*(!=|>=|<=|=|>|<|LIKE)\s*(.+)$/i);
  if (!match) throw new Error(`could not parse condition "${trimmed}"`);
  const [, field, opRaw, rawValue] = match;
  const op = opRaw.toUpperCase();
  const value = parseValue(rawValue);
  return (record) => {
    const actual = fieldResolver(record, field);
    if (op === "LIKE") return typeof actual === "string" && likeToRegex(value).test(actual);
    if (actual === undefined || actual === null) return false;
    if (op === "=") return String(actual).toLowerCase() === String(value).toLowerCase();
    if (op === "!=") return String(actual).toLowerCase() !== String(value).toLowerCase();
    const a = Number(actual);
    const b = Number(value);
    const numeric = !Number.isNaN(a) && !Number.isNaN(b);
    if (op === ">") return numeric ? a > b : String(actual) > String(value);
    if (op === ">=") return numeric ? a >= b : String(actual) >= String(value);
    if (op === "<") return numeric ? a < b : String(actual) < String(value);
    if (op === "<=") return numeric ? a <= b : String(actual) <= String(value);
    return false;
  };
}

/**
 * Compile a query string into a `record => boolean` predicate, or `null`
 * for an empty/trivial ("WHERE 1=1") query. Throws on a malformed
 * condition; callers should catch this and surface it as a query error
 * rather than letting it propagate.
 */
export function compileQuery(raw, fieldResolver) {
  let text = (raw || "").trim();
  if (!text) return null;
  text = text.replace(/^select\s+\*\s*(from\s+\w+\s*)?where\s+/i, "").replace(/^where\s+/i, "").trim();
  if (!text || /^1\s*=\s*1$/.test(text)) return null;

  const tokens = text.split(/\s+(AND|OR)\s+/i);
  const predicates = [];
  const ops = [];
  for (let i = 0; i < tokens.length; i += 2) {
    predicates.push(compileCondition(tokens[i], fieldResolver));
    if (tokens[i + 1]) ops.push(tokens[i + 1].toUpperCase());
  }

  return (record) => {
    let result = predicates[0](record);
    for (let i = 0; i < ops.length; i++) {
      result = ops[i] === "OR" ? result || predicates[i + 1](record) : result && predicates[i + 1](record);
    }
    return result;
  };
}
