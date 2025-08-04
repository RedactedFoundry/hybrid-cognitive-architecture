# ADR-002: Use TigerGraph Over PostgreSQL for Agent Genome Storage

**Date**: 2024-11-20  
**Status**: Accepted  
**Deciders**: Project Lead

## Context

The Hybrid AI Council's KIP (Knowledge-Incentive Protocol) layer requires persistent storage for autonomous agent "genomes" - the configuration, capabilities, relationships, and performance data that define each agent. The system needs to store complex relationships between agents, tools, transactions, and performance metrics while supporting graph-based queries for agent optimization and analysis.

## Decision

**Use TigerGraph Community Edition for agent genome and relationship storage instead of PostgreSQL.**

## Rationale

### Why TigerGraph Won

1. **Natural Relationship Modeling**: Agent-tool-transaction relationships are inherently graph-based
2. **Performance Analytics**: Built-in graph algorithms for agent performance analysis
3. **Economic Network Analysis**: Can model agent interactions and resource sharing
4. **Scalability**: Designed for complex relationship queries
5. **Agent Evolution**: Support for genetic algorithms and agent breeding
6. **Zero License Cost**: Community Edition supports up to 2.4TB free

### Alternatives Considered

1. **PostgreSQL with JSON**: Relational database with JSON columns
   - **Rejected**: Complex JOIN queries for relationship analysis, poor performance for graph traversals
   
2. **Neo4j**: Another graph database option
   - **Rejected**: Commercial licensing costs, more complex deployment
   
3. **MongoDB**: Document database
   - **Rejected**: No native graph relationship support, complex aggregation pipelines needed

## Consequences

### Positive
- ✅ **Intuitive Data Modeling**: Agent relationships map naturally to graph structure
- ✅ **Powerful Analytics**: Built-in algorithms for network analysis and optimization
- ✅ **Future-Proof Architecture**: Supports advanced agent breeding and evolution
- ✅ **Performance**: Optimized for relationship queries and traversals
- ✅ **Economic Modeling**: Can track value flows between agents and resources
- ✅ **Cost Effective**: Free Community Edition sufficient for single-user deployment

### Negative  
- ❌ **Learning Curve**: GSQL query language vs familiar SQL
- ❌ **Deployment Complexity**: More complex setup than PostgreSQL
- ❌ **Tool Ecosystem**: Fewer third-party tools compared to PostgreSQL
- ❌ **Backup/Recovery**: Less familiar backup procedures
- ❌ **Community Size**: Smaller community than PostgreSQL

### Neutral
- Docker deployment available for both options
- Both support ACID transactions and data consistency

## Implementation Notes

### Schema Design
- **KIPAgent** vertices: Core agent identity and configuration
- **Tool** vertices: Available tools and capabilities  
- **Transaction** vertices: Financial and action history
- **AgentBudget** vertices: Financial status and limits
- **Uses** edges: Agent-tool relationships with authorization
- **Executes** edges: Agent-transaction relationships with outcomes

### Key Queries
- Agent performance analysis: `INTERPRET QUERY AgentROIAnalysis(...)`
- Tool usage patterns: `INTERPRET QUERY ToolUsageStats(...)`
- Economic flow analysis: `INTERPRET QUERY SystemEconomics(...)`

### Deployment
- TigerGraph Community Edition 4.2.0
- Docker container with persistent volume
- GSQL schema initialization via `scripts/init_tigergraph.py`
- Default credentials: `tigergraph/tigergraph` (configurable via .env)

## References

- [TigerGraph Community Edition Documentation](https://docs.tigergraph.com/tigergraph-server/current/getting-started/)
- [GSQL Language Reference](https://docs.tigergraph.com/gsql-ref/current/intro/)
- Project schema file: `schemas/schema.gsql`
- Setup documentation: `docs/TigerGraph_Community_Edition_Setup.md`