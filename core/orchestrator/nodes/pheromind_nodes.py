#!/usr/bin/env python3
"""
Pheromind Processing Node - Ambient Pattern Detection

This module contains the Pheromind logic for ambient pattern detection and discovery.
Pheromind queries Redis-based signals for existing patterns that match user context.
"""

from typing import List

from core.pheromind import PheromindSignal, pheromind_session
from .base import CognitiveProcessingNode
from ..models import OrchestratorState, ProcessingPhase


class PheromindNode(CognitiveProcessingNode):
    """
    Pheromind - Ambient Pattern Detection Layer.
    
    This layer queries the Redis-based pheromind signals for existing patterns
    that match the user's input, providing ambient context for other cognitive layers.
    """
    
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """Process Pheromind ambient pattern detection."""
        return await self.pheromind_scan_node(state)
    
    async def pheromind_scan_node(self, state: OrchestratorState) -> OrchestratorState:
        """
        Execute Pheromind ambient pattern detection.
        
        This method queries the Redis-based pheromind layer for existing signals
        that match patterns in the user's input, providing ambient context for
        the council deliberation.
        """
        self.logger.info(
            "Starting Pheromind ambient scan", 
            request_id=state.request_id,
            user_input_preview=state.user_input[:100]
        )
        state.update_phase(ProcessingPhase.PHEROMIND_SCAN)
        
        try:
            # Use pheromind session for ambient intelligence query
            async with pheromind_session() as pheromind:
                # Extract keywords from user input for pattern matching
                search_patterns = self._extract_search_patterns(state.user_input)
                
                # Query for existing pheromind signals matching user context
                all_signals = []
                for pattern in search_patterns:
                    signals = await pheromind.query_signals(pattern, min_strength=0.3)
                    all_signals.extend(signals)
                
                # Remove duplicates while preserving strength-based ordering
                unique_signals = self._deduplicate_signals(all_signals)
                
                # Update state with discovered ambient signals
                state.pheromind_signals.extend(unique_signals)
                
                self.logger.info(
                    "Pheromind scan completed",
                    request_id=state.request_id,
                    signals_found=len(unique_signals),
                    search_patterns=search_patterns,
                    strongest_signal=max([s.strength for s in unique_signals], default=0.0)
                )
                
        except Exception as e:
            # Pheromind failures should not block the main flow
            self.logger.warning(
                "Pheromind scan failed, continuing without ambient context",
                request_id=state.request_id,
                error=str(e),
                error_type=type(e).__name__
            )
            # Continue processing even if pheromind is unavailable
        
        return state
    
    def _extract_search_patterns(self, user_input: str) -> List[str]:
        """
        Extract search patterns from user input for pheromind querying.
        
        This method identifies key terms and concepts that could match
        existing pheromind signals in Redis.
        
        Args:
            user_input: The user's query text
            
        Returns:
            List[str]: Search patterns for pheromind queries
        """
        # Convert to lowercase for pattern matching
        input_lower = user_input.lower()
        
        # Extract key terms (simple keyword matching for MVP)
        # FUTURE: Could enhance with spaCy/NLTK for entity recognition and semantic clustering
        patterns = []
        
        # Broad pattern: search for any signals
        patterns.append("*")
        
        # Domain-specific patterns
        if any(word in input_lower for word in ['ai', 'artificial', 'intelligence', 'model', 'llm']):
            patterns.append("*ai*")
            patterns.append("*intelligence*")
            
        if any(word in input_lower for word in ['tech', 'technology', 'computer', 'software']):
            patterns.append("*tech*")
            patterns.append("*technology*")
            
        if any(word in input_lower for word in ['help', 'question', 'ask', 'how', 'what', 'why']):
            patterns.append("*question*")
            patterns.append("*help*")
            
        if any(word in input_lower for word in ['complex', 'difficult', 'hard', 'complicated']):
            patterns.append("*complexity*")
            patterns.append("*complex*")
            
        if any(word in input_lower for word in ['creative', 'idea', 'brainstorm', 'think']):
            patterns.append("*creative*")
            patterns.append("*idea*")
            
        # Remove duplicates while preserving order
        seen = set()
        unique_patterns = []
        for pattern in patterns:
            if pattern not in seen:
                seen.add(pattern)
                unique_patterns.append(pattern)
                
        return unique_patterns
    
    def _deduplicate_signals(self, signals: List[PheromindSignal]) -> List[PheromindSignal]:
        """
        Remove duplicate pheromind signals while preserving strongest signals.
        
        Args:
            signals: List of potentially duplicate signals
            
        Returns:
            List[PheromindSignal]: Deduplicated signals sorted by strength
        """
        if not signals:
            return []
            
        # Group by pattern_id and keep strongest signal for each pattern
        pattern_map = {}
        for signal in signals:
            if (signal.pattern_id not in pattern_map or 
                signal.strength > pattern_map[signal.pattern_id].strength):
                pattern_map[signal.pattern_id] = signal
                
        # Return sorted by strength (strongest first)
        unique_signals = list(pattern_map.values())
        unique_signals.sort(key=lambda s: s.strength, reverse=True)
        
        return unique_signals