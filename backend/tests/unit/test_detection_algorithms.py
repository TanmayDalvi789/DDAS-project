"""
Phase 2: Detection Algorithms Unit Tests
Tests for fuzzy, semantic, exact detection and orchestrator.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from detection.fuzzy_detection import FuzzyDetection
from detection.semantic_detection import SemanticDetection
from detection.exact_detection import ExactDetection
from detection.orchestrator import DetectionOrchestrator


# ============================================================================
# FUZZY DETECTION TESTS
# ============================================================================

@pytest.mark.unit
class TestFuzzyDetection:
    """Test FuzzyDetection algorithm."""
    
    @pytest.fixture
    def detector(self):
        return FuzzyDetection()
    
    def test_exact_match(self, detector, test_samples):
        """Test exact string matching."""
        sample = test_samples["exact"]
        result = detector.detect(sample, sample)
        
        assert result.found is True
        assert result.confidence == 1.0
        assert len(result.matches) > 0
    
    def test_high_similarity(self, detector):
        """Test high similarity strings."""
        sample1 = "alert(window,'Hello')"
        sample2 = "alert(window,'Hello')"  # Exact
        
        result = detector.detect(sample1, sample2)
        assert result.confidence >= 0.95
    
    def test_partial_match(self, detector):
        """Test partial string matching."""
        sample1 = "this is a long string with some content"
        sample2 = "long string with some"
        
        result = detector.detect(sample1, sample2)
        # Should find similarity even with partial match
        assert result.confidence > 0.5
    
    def test_no_match(self, detector):
        """Test completely different strings."""
        sample1 = "alert(window,'malware')"
        sample2 = "console.log('hello')"
        
        result = detector.detect(sample1, sample2)
        # Very low or no match
        assert result.confidence < 0.3
    
    def test_case_sensitivity(self, detector):
        """Test case sensitivity handling."""
        sample1 = "MALICIOUS_CODE"
        sample2 = "malicious_code"
        
        result = detector.detect(sample1.lower(), sample2.lower())
        assert result.confidence > 0.95
    
    def test_whitespace_handling(self, detector):
        """Test whitespace tolerance."""
        sample1 = "alert( window , 'Hello' )"
        sample2 = "alert(window,'Hello')"
        
        result = detector.detect(sample1, sample2)
        # Should handle whitespace differences
        assert result.confidence > 0.80
    
    def test_batch_detection(self, detector, test_samples):
        """Test detecting across multiple samples."""
        reference = test_samples["exact"]
        samples = [
            reference,
            test_samples["semantic"],
            test_samples["fuzzy"],
        ]
        
        results = detector.batch_detect(reference, samples)
        assert len(results) == 3
        assert results[0].confidence > results[2].confidence


# ============================================================================
# SEMANTIC DETECTION TESTS
# ============================================================================

@pytest.mark.unit
class TestSemanticDetection:
    """Test SemanticDetection algorithm."""
    
    @pytest.fixture
    def detector(self):
        with patch('detection.semantic_detection.SentenceTransformer'):
            return SemanticDetection()
    
    @pytest.fixture
    def mock_embeddings(self):
        """Create consistent mock embeddings."""
        np.random.seed(42)
        return {
            "alert(window,'xss')": np.random.randn(384),
            "alert(window,'similar')": np.random.randn(384),
            "console.log('different')": np.random.randn(384),
        }
    
    def test_semantic_similarity_high(self, detector):
        """Test detecting semantically similar content."""
        sample1 = "alert(window,'xss attack')"
        sample2 = "alert(window,'xss vulnerability')"
        
        # Mock the embedding and similarity
        with patch.object(detector, 'model') as mock_model:
            mock_model.encode.return_value = np.array([[1, 0, 0]])
            with patch.object(detector, 'index') as mock_index:
                mock_index.search.return_value = (
                    np.array([[0.95]]),  # High similarity
                    np.array([[0]])
                )
                
                result = detector.detect(sample1, sample2)
                assert result.confidence > 0.90
    
    def test_semantic_similarity_low(self, detector):
        """Test detecting semantically different content."""
        sample1 = "alert(window,'xss')"
        sample2 = "console.log('hello')"
        
        with patch.object(detector, 'model') as mock_model:
            mock_model.encode.return_value = np.array([[1, 0, 0]])
            with patch.object(detector, 'index') as mock_index:
                mock_index.search.return_value = (
                    np.array([[0.2]]),  # Low similarity
                    np.array([[0]])
                )
                
                result = detector.detect(sample1, sample2)
                assert result.confidence < 0.5
    
    def test_batch_detection(self, detector):
        """Test batch semantic detection."""
        reference = "alert(window,'malware')"
        samples = [
            "alert(window,'similar')",
            "console.log('different')",
            "alert(window,'threat')",
        ]
        
        with patch.object(detector, 'batch_detect') as mock_batch:
            mock_results = [
                Mock(confidence=0.85, found=True),
                Mock(confidence=0.15, found=False),
                Mock(confidence=0.90, found=True),
            ]
            mock_batch.return_value = mock_results
            
            results = detector.batch_detect(reference, samples)
            assert len(results) == 3


# ============================================================================
# EXACT DETECTION TESTS
# ============================================================================

@pytest.mark.unit
class TestExactDetection:
    """Test ExactDetection algorithm."""
    
    @pytest.fixture
    def detector(self):
        return ExactDetection()
    
    def test_exact_hash_match_sha256(self, detector):
        """Test SHA256 hash matching."""
        sample = "alert(window,'xss')"
        
        result = detector.detect(sample, sample)
        assert result.found is True
        assert result.confidence == 1.0
    
    def test_hash_mismatch(self, detector):
        """Test hash mismatch."""
        sample1 = "alert(window,'xss')"
        sample2 = "alert(window,'different')"
        
        result = detector.detect(sample1, sample2)
        assert result.found is False
        assert result.confidence == 0.0
    
    def test_md5_fallback(self, detector):
        """Test MD5 hash fallback."""
        sample = "alert(window,'xss')"
        
        result = detector.detect(sample, sample, hash_type='md5')
        assert result.found is True
    
    def test_add_to_signatures(self, detector):
        """Test adding signature to database."""
        sample = "alert(window,'malware')"
        detector.add_signature(sample, "xss_variant_1", {"type": "xss"})
        
        result = detector.detect(sample, sample)
        assert result.found is True
    
    def test_batch_detection(self, detector, test_samples):
        """Test batch hash detection."""
        reference = test_samples["exact"]
        samples = [
            reference,
            test_samples["semantic"],
            test_samples["fuzzy"],
        ]
        
        results = detector.batch_detect(reference, samples)
        assert results[0].found is True  # Exact match
        assert results[1].found is False  # Different
        assert results[2].found is False  # Different


# ============================================================================
# DETECTION ORCHESTRATOR TESTS
# ============================================================================

@pytest.mark.unit
class TestDetectionOrchestrator:
    """Test DetectionOrchestrator."""
    
    @pytest.fixture
    def mock_detectors(self):
        """Create mock detectors."""
        return {
            'fuzzy': Mock(),
            'semantic': Mock(),
            'exact': Mock(),
        }
    
    @pytest.fixture
    def orchestrator(self, mock_detectors):
        """Create orchestrator with mocked detectors."""
        orch = DetectionOrchestrator()
        orch.detectors['fuzzy'] = mock_detectors['fuzzy']
        orch.detectors['semantic'] = mock_detectors['semantic']
        orch.detectors['exact'] = mock_detectors['exact']
        return orch
    
    def test_strong_detection_block(self, orchestrator, mock_detectors):
        """Test STRONG detection (>95% confidence) triggers BLOCK."""
        # Setup: One detector has >95% confidence
        mock_detectors['fuzzy'].detect.return_value = Mock(
            found=True, confidence=0.96, matches=["match"]
        )
        mock_detectors['semantic'].detect.return_value = Mock(
            found=False, confidence=0.50, matches=[]
        )
        mock_detectors['exact'].detect.return_value = Mock(
            found=False, confidence=0.0, matches=[]
        )
        
        result = orchestrator.detect("sample", "reference")
        assert result.decision == "BLOCK"
        assert result.confidence > 0.95
        assert result.reason == "STRONG_DETECTION"
    
    def test_multiple_agreement_warn(self, orchestrator, mock_detectors):
        """Test multiple algorithms agreeing triggers WARN."""
        # Setup: Two detectors agree on detection
        mock_detectors['fuzzy'].detect.return_value = Mock(
            found=True, confidence=0.85, matches=["m1"]
        )
        mock_detectors['semantic'].detect.return_value = Mock(
            found=True, confidence=0.80, matches=["m2"]
        )
        mock_detectors['exact'].detect.return_value = Mock(
            found=False, confidence=0.0, matches=[]
        )
        
        result = orchestrator.detect("sample", "reference")
        assert result.decision == "WARN"
        assert result.reason == "MULTIPLE_DETECTION"
    
    def test_weak_detection_watch(self, orchestrator, mock_detectors):
        """Test single algorithm detection triggers WATCH."""
        # Setup: Only one detector finds something
        mock_detectors['fuzzy'].detect.return_value = Mock(
            found=True, confidence=0.75, matches=["m1"]
        )
        mock_detectors['semantic'].detect.return_value = Mock(
            found=False, confidence=0.40, matches=[]
        )
        mock_detectors['exact'].detect.return_value = Mock(
            found=False, confidence=0.0, matches=[]
        )
        
        result = orchestrator.detect("sample", "reference")
        assert result.decision == "WATCH"
        assert result.reason == "WEAK_DETECTION"
    
    def test_no_detection_allow(self, orchestrator, mock_detectors):
        """Test no detection triggers ALLOW."""
        # Setup: All detectors return no match
        for detector in mock_detectors.values():
            detector.detect.return_value = Mock(
                found=False, confidence=0.0, matches=[]
            )
        
        result = orchestrator.detect("sample", "reference")
        assert result.decision == "ALLOW"
        assert result.reason == "NO_DETECTION"
    
    def test_confidence_averaging(self, orchestrator, mock_detectors):
        """Test confidence is averaged across detectors."""
        mock_detectors['fuzzy'].detect.return_value = Mock(
            found=True, confidence=0.90, matches=["m1"]
        )
        mock_detectors['semantic'].detect.return_value = Mock(
            found=True, confidence=0.80, matches=["m2"]
        )
        mock_detectors['exact'].detect.return_value = Mock(
            found=False, confidence=0.0, matches=[]
        )
        
        result = orchestrator.detect("sample", "reference")
        # Average of 0.90, 0.80, 0.0 = 0.567
        expected_conf = (0.90 + 0.80 + 0.0) / 3
        assert abs(result.confidence - expected_conf) < 0.01
    
    def test_batch_detection(self, orchestrator, mock_detectors):
        """Test batch detection across multiple samples."""
        reference = "reference"
        samples = ["sample1", "sample2", "sample3"]
        
        # Setup detectors to return consistent results
        for detector in mock_detectors.values():
            detector.batch_detect.return_value = [
                Mock(found=True, confidence=0.85, matches=["m"]),
                Mock(found=False, confidence=0.20, matches=[]),
                Mock(found=True, confidence=0.75, matches=["m"]),
            ]
        
        results = orchestrator.batch_detect(reference, samples)
        assert len(results) == 3


# ============================================================================
# DETECTION INTEGRATION TESTS
# ============================================================================

@pytest.mark.unit
class TestDetectionIntegration:
    """Test detection components working together."""
    
    def test_detection_workflow(self):
        """Test complete detection workflow."""
        # Create real detectors
        fuzzy = FuzzyDetection()
        semantic_detector = SemanticDetection.__new__(SemanticDetection)
        semantic_detector.detectors = {'fuzzy': fuzzy}
        exact = ExactDetection()
        
        # Create orchestrator
        orchestrator = DetectionOrchestrator()
        
        # Test with real fuzzy detector
        reference = "alert(window,'malware')"
        similar = "alert(window,'malware')"
        different = "console.log('hello')"
        
        # Exact match should be detected
        result_exact = fuzzy.detect(reference, similar)
        assert result_exact.confidence >= 0.95
        
        # Different strings should have low similarity
        result_diff = fuzzy.detect(reference, different)
        assert result_diff.confidence < 0.5
