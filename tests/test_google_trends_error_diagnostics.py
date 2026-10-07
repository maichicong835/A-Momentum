import importlib.util
import pathlib
import unittest

path=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"google_trends.py"
spec=importlib.util.spec_from_file_location("a_momentum_gt_diagnostics",path)
gt=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gt)

class SensorErrorDiagnosticTests(unittest.TestCase):
    def test_known_empty_native_series_is_a_safe_code(self):
        d=gt.safe_exception_diagnostic(RuntimeError("EMPTY_NATIVE_SERIES"),"VALIDATE_NATIVE_SERIES")
        self.assertEqual(d,{"error_stage":"VALIDATE_NATIVE_SERIES","error_code":"EMPTY_NATIVE_SERIES"})

    def test_known_completed_blocks_failure_is_a_safe_code(self):
        d=gt.safe_exception_diagnostic(RuntimeError("COMPLETED_24H_BLOCKS_LT_3"),"VALIDATE_COMPLETED_BLOCKS")
        self.assertEqual(d["error_code"],"COMPLETED_24H_BLOCKS_LT_3")

    def test_provider_exception_message_not_exposed(self):
        d=gt.safe_exception_diagnostic(RuntimeError("http error?token=PRIVATE_SECRET"),"FETCH_NATIVE_SERIES")
        self.assertEqual(d["error_code"],"UNCLASSIFIED_PROVIDER_OR_LIBRARY_EXCEPTION")
        self.assertEqual(d["error_stage"],"FETCH_NATIVE_SERIES")
        self.assertNotIn("PRIVATE_SECRET",repr(d))

    def test_known_error_text_from_untrusted_stage_not_misclassified(self):
        d=gt.safe_exception_diagnostic(RuntimeError("EMPTY_NATIVE_SERIES"),"FETCH_NATIVE_SERIES")
        self.assertEqual(d["error_code"],"UNCLASSIFIED_PROVIDER_OR_LIBRARY_EXCEPTION")

    def test_non_runtime_exception_does_not_become_shape_evidence(self):
        d=gt.safe_exception_diagnostic(ValueError("COMPLETED_24H_BLOCKS_LT_3"),"VALIDATE_COMPLETED_BLOCKS")
        self.assertEqual(d["error_code"],"UNCLASSIFIED_PROVIDER_OR_LIBRARY_EXCEPTION")

if __name__=="__main__":
    unittest.main()
