# ragcheckup

**Eval tools tell you your score dropped. ragcheckup tells you which chunks are broken and why.**

ragcheckup is an open-source CLI and Python library that inspects the index behind a RAG
system (a chunk export file or a live vector database) and reports the structural
problems that make retrieval fail in production: shredded tables, chunks that lost their
context, exact-string lookups that vector search misses, conflicting document versions,
and basic index hygiene. Every finding points at specific chunk IDs and links to a fix.

> **Status: design stage.** No code yet. See the design documents below.

## Design

- [Product requirements](docs/PRD.md)
- [Technical design](docs/TECHNICAL_DESIGN.md)

## Acknowledgements

The baseline structural checks are inspired by
[ChunkLint](https://github.com/prabhath004/chunkLint) (MIT).

## License

[MIT](LICENSE)
