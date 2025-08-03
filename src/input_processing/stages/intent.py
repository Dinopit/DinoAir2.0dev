"""Intent classification module for understanding user input types.

Classifies user input into different intent categories to enable
appropriate handling and response strategies.
"""

from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass
import re
from datetime import datetime


class IntentType(Enum):
    """Types of user intents."""
    COMMAND = "command"          # Direct command to execute
    QUERY = "query"              # Information request
    CONVERSATION = "conversation" # Casual chat
    CODE = "code"                # Code snippet or request
    UNCLEAR = "unclear"          # Cannot determine intent


@dataclass
class IntentClassification:
    """Result of intent classification."""
    primary_intent: IntentType
    confidence: float  # 0-1 confidence score
    secondary_intents: List[Tuple[IntentType, float]]  # Other possible intents
    extracted_entities: Dict[str, Any]  # Extracted entities (commands, topics, etc.)
    reasoning: str  # Brief explanation of classification


class IntentClassifier:
    """Classifies user input into intent categories.
    
    This classifier uses pattern matching and heuristics to determine
    the most likely intent of user input, enabling appropriate handling.
    """
    
    def __init__(self):
        """Initialize with intent patterns and indicators."""
        # Command patterns
        self.command_patterns = [
            # Watchdog commands
            r'^(start|stop|restart|pause|resume)\s+watchdog',
            r'^watchdog\s+(start|stop|restart|status|info)',
            r'^(show|display|get)\s+watchdog\s+(status|info|metrics)',
            
            # System commands
            r'^(clear|reset|clean)\s+(chat|history|screen)',
            r'^(save|export|backup)\s+(chat|conversation|history)',
            r'^(load|import|restore)\s+\w+',
            r'^(help|commands?|what can you do)',
            r'^(exit|quit|bye|goodbye)',
            
            # File operations
            r'^(open|read|show|display)\s+.*\.(txt|pdf|doc|py|js|html)',
            r'^(save|write|create)\s+.*\.(txt|pdf|doc|py|js|html)',
            r'^(delete|remove|rm)\s+',
            
            # Settings/config
            r'^(set|change|update|modify)\s+\w+\s+to\s+',
            r'^(enable|disable|turn\s+(on|off))\s+',
            r'^configure\s+',
        ]
        
        # Query indicators
        self.query_indicators = [
            r'^(what|when|where|who|why|how|which)\s+',
            r'^(is|are|was|were|will|would|can|could|should)\s+',
            r'^(tell|show|explain|describe)\s+me\s+',
            r'^(do|does|did)\s+',
            r'\?$',  # Ends with question mark
            r'^(find|search|look\s+for)\s+',
            r'^(list|enumerate|show\s+all)\s+',
        ]
        
        # Code indicators
        self.code_indicators = [
            r'```[\s\S]*```',  # Code blocks
            r'`[^`]+`',        # Inline code
            r'(function|def|class|import|from|return)\s+',
            r'(if|else|elif|for|while|try|except)\s*:',
            r'[(){}\[\]]',     # Programming brackets
            r'(==|!=|<=|>=|\+=|-=|\*=|/=)',  # Operators
            r'\b(var|let|const|public|private|static)\s+',
            r'(\.py|\.js|\.java|\.cpp|\.cs|\.rb)(\s|$)',
            r'^(write|create|implement|code)\s+.*\s+(function|method|class)',
        ]
        
        # Conversation indicators
        self.conversation_indicators = [
            r'^(hi|hello|hey|greetings)',
            r'^(thanks|thank you|thx|ty)',
            r'^(good\s+(morning|afternoon|evening|night))',
            r'^(how\s+are\s+you|how\'s\s+it\s+going)',
            r'^(nice|great|awesome|cool|interesting)',
            r'^(ok|okay|sure|yes|no|maybe)',
            r'^(i\s+(think|feel|believe|want|need))',
            r'^(sorry|excuse\s+me|pardon)',
        ]
        
        # Entity extraction patterns
        self.entity_patterns = {
            'filepath': r'(?:[a-zA-Z]:)?(?:[\\/][^\\/\s]+)+\.\w+',
            'url': r'https?://[^\s]+',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'number': r'\b\d+(?:\.\d+)?\b',
            'time': r'\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[ap]m)?\b',
            'date': r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        }
        
        # Intent keywords for quick classification
        self.intent_keywords = {
            IntentType.COMMAND: {
                'start', 'stop', 'run', 'execute', 'launch', 'kill',
                'clear', 'reset', 'save', 'load', 'export', 'import',
                'enable', 'disable', 'configure', 'set', 'change'
            },
            IntentType.QUERY: {
                'what', 'when', 'where', 'who', 'why', 'how',
                'explain', 'describe', 'show', 'tell', 'find',
                'search', 'list', 'status', 'info', 'help'
            },
            IntentType.CODE: {
                'function', 'method', 'class', 'variable', 'code',
                'implement', 'create', 'write', 'debug', 'fix',
                'refactor', 'optimize', 'algorithm', 'script'
            },
            IntentType.CONVERSATION: {
                'hello', 'hi', 'thanks', 'bye', 'good', 'nice',
                'feel', 'think', 'believe', 'want', 'need',
                'sorry', 'please', 'sure', 'okay'
            }
        }
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of entity types to extracted values
        """
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        # Extract potential command names
        command_matches = []
        for pattern in self.command_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                command_matches.append(match.group())
        
        if command_matches:
            entities['commands'] = command_matches
        
        return entities
    
    def _calculate_pattern_scores(self, text: str) -> Dict[IntentType, float]:
        """Calculate pattern matching scores for each intent type.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of intent types to scores
        """
        scores = {intent: 0.0 for intent in IntentType}
        text_lower = text.lower()
        
        # Check command patterns
        command_score = 0.0
        for pattern in self.command_patterns:
            if re.search(pattern, text_lower):
                command_score += 1.0
        scores[IntentType.COMMAND] = min(command_score, 1.0)
        
        # Check query indicators
        query_score = 0.0
        for pattern in self.query_indicators:
            if re.search(pattern, text_lower):
                query_score += 0.5
        scores[IntentType.QUERY] = min(query_score, 1.0)
        
        # Check code indicators
        code_score = 0.0
        for pattern in self.code_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                code_score += 0.5
        scores[IntentType.CODE] = min(code_score, 1.0)
        
        # Check conversation indicators
        conv_score = 0.0
        for pattern in self.conversation_indicators:
            if re.search(pattern, text_lower):
                conv_score += 0.5
        scores[IntentType.CONVERSATION] = min(conv_score, 1.0)
        
        return scores
    
    def _calculate_keyword_scores(self, text: str) -> Dict[IntentType, float]:
        """Calculate keyword-based scores for each intent type.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary of intent types to scores
        """
        scores = {intent: 0.0 for intent in IntentType}
        words = set(text.lower().split())
        
        for intent_type, keywords in self.intent_keywords.items():
            matching_keywords = words.intersection(keywords)
            if matching_keywords:
                # Score based on percentage of keywords found
                scores[intent_type] = len(matching_keywords) / len(keywords)
        
        return scores
    
    def _combine_scores(self, pattern_scores: Dict[IntentType, float],
                       keyword_scores: Dict[IntentType, float]) -> Dict[IntentType, float]:
        """Combine pattern and keyword scores.
        
        Args:
            pattern_scores: Scores from pattern matching
            keyword_scores: Scores from keyword matching
            
        Returns:
            Combined scores
        """
        combined = {}
        
        for intent_type in IntentType:
            if intent_type == IntentType.UNCLEAR:
                continue
                
            # Weight pattern matches more heavily than keywords
            pattern_weight = 0.7
            keyword_weight = 0.3
            
            combined[intent_type] = (
                pattern_scores.get(intent_type, 0) * pattern_weight +
                keyword_scores.get(intent_type, 0) * keyword_weight
            )
        
        return combined
    
    def classify(self, text: str) -> IntentClassification:
        """Classify the intent of user input.
        
        Args:
            text: User input text
            
        Returns:
            IntentClassification with results
        """
        if not text or not text.strip():
            return IntentClassification(
                primary_intent=IntentType.UNCLEAR,
                confidence=1.0,
                secondary_intents=[],
                extracted_entities={},
                reasoning="Empty or whitespace-only input"
            )
        
        # Extract entities
        entities = self._extract_entities(text)
        
        # Calculate scores
        pattern_scores = self._calculate_pattern_scores(text)
        keyword_scores = self._calculate_keyword_scores(text)
        combined_scores = self._combine_scores(pattern_scores, keyword_scores)
        
        # Sort intents by score
        sorted_intents = sorted(
            combined_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Determine primary intent
        if not sorted_intents or sorted_intents[0][1] < 0.2:
            # No clear intent
            return IntentClassification(
                primary_intent=IntentType.UNCLEAR,
                confidence=0.8,
                secondary_intents=sorted_intents[:3],
                extracted_entities=entities,
                reasoning="No clear intent patterns detected"
            )
        
        primary_intent, primary_score = sorted_intents[0]
        
        # Build secondary intents list
        secondary_intents = [
            (intent, score) for intent, score in sorted_intents[1:]
            if score > 0.1  # Only include if somewhat confident
        ][:3]  # Max 3 secondary intents
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            primary_intent, primary_score, pattern_scores, keyword_scores
        )
        
        return IntentClassification(
            primary_intent=primary_intent,
            confidence=primary_score,
            secondary_intents=secondary_intents,
            extracted_entities=entities,
            reasoning=reasoning
        )
    
    def _generate_reasoning(self, intent: IntentType, score: float,
                          pattern_scores: Dict[IntentType, float],
                          keyword_scores: Dict[IntentType, float]) -> str:
        """Generate reasoning for the classification.
        
        Args:
            intent: Primary intent
            score: Confidence score
            pattern_scores: Pattern matching scores
            keyword_scores: Keyword matching scores
            
        Returns:
            Reasoning string
        """
        reasons = []
        
        if pattern_scores.get(intent, 0) > 0.5:
            reasons.append("strong pattern match")
        elif pattern_scores.get(intent, 0) > 0:
            reasons.append("pattern indicators present")
            
        if keyword_scores.get(intent, 0) > 0.5:
            reasons.append("multiple relevant keywords")
        elif keyword_scores.get(intent, 0) > 0:
            reasons.append("some keywords detected")
        
        if score > 0.8:
            confidence = "High confidence"
        elif score > 0.5:
            confidence = "Moderate confidence"
        else:
            confidence = "Low confidence"
            
        if reasons:
            return f"{confidence} based on {' and '.join(reasons)}"
        else:
            return f"{confidence} classification"
    
    def get_intent_description(self, intent_type: IntentType) -> str:
        """Get a description of what an intent type means.
        
        Args:
            intent_type: The intent type
            
        Returns:
            Description string
        """
        descriptions = {
            IntentType.COMMAND: "User wants to execute a specific action or command",
            IntentType.QUERY: "User is asking for information or requesting data",
            IntentType.CONVERSATION: "User is engaging in casual conversation",
            IntentType.CODE: "User is providing or requesting code",
            IntentType.UNCLEAR: "Cannot determine clear intent from input"
        }
        
        return descriptions.get(intent_type, "Unknown intent type")


# Convenience function
def classify_intent(text: str) -> IntentType:
    """Quick intent classification.
    
    Args:
        text: User input text
        
    Returns:
        Primary intent type
    """
    classifier = IntentClassifier()
    result = classifier.classify(text)
    return result.primary_intent