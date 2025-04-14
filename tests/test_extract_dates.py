import unittest
import os
import numpy as np
import fitz  

try:
    from ox_extract_dates import (
        extract_text_from_pdf,
        extract_and_analyze_dates,
    )
    MODULE_FOUND = True
except ImportError as e:
    print(f"Error importing main module: {e}")
    print("Make sure the file 'date_extractor_pdf.py' is in the correct location.")

    MODULE_FOUND = False

    def extract_text_from_pdf(pdf_path): raise ImportError("Module not found")
    def extract_and_analyze_dates(text): raise ImportError("Module not found")

TEST_PDF_FILENAME = "temp_test_document.pdf"
TEST_PDF_TEXT_PAGE1 = "Texto da página 1 com o ano 1750."
TEST_PDF_TEXT_PAGE2 = "Continuação na página 2 sobre o século XVIII."

@unittest.skipIf(not MODULE_FOUND, "Main module not found, skipping tests.")
class TestDateExtractorWithPDF(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Creates a temporary PDF file before all tests."""
        try:
            doc = fitz.open() 
           
            page1 = doc.new_page()
            page1.insert_text((72, 72), TEST_PDF_TEXT_PAGE1) 
            
            page2 = doc.new_page()
            page2.insert_text((72, 72), TEST_PDF_TEXT_PAGE2) 
            doc.save(TEST_PDF_FILENAME)
            doc.close()
            print(f"\nTest PDF file '{TEST_PDF_FILENAME}' created.")

        except Exception as e:
            print(f"Failed to create test PDF: {e}")
            
            raise unittest.SkipTest(f"Could not create test PDF: {e}")


    @classmethod
    def tearDownClass(cls):
        """Removes the temporary PDF file after all tests."""
        if os.path.exists(TEST_PDF_FILENAME):
            os.remove(TEST_PDF_FILENAME)
            print(f"Test PDF file '{TEST_PDF_FILENAME}' removed.")

    def test_pdf_extraction_success(self):
        """Tests text extraction from a valid PDF."""

        extracted_text = extract_text_from_pdf(TEST_PDF_FILENAME)
        self.assertIsNotNone(extracted_text)
        self.assertIn(TEST_PDF_TEXT_PAGE1, extracted_text)
        self.assertIn(TEST_PDF_TEXT_PAGE2, extracted_text)

        self.assertEqual(extracted_text.strip(), (TEST_PDF_TEXT_PAGE1 + "\n" + TEST_PDF_TEXT_PAGE2).strip())

    def test_pdf_extraction_nonexistent_file(self):
        """Tests extraction with a non-existent PDF file path."""

        extracted_text = extract_text_from_pdf("file_that_does_not_exist.pdf")
        self.assertIsNone(extracted_text)

    def test_pdf_extraction_invalid_path(self):
        """Tests extraction with invalid path input (None)."""
        extracted_text = extract_text_from_pdf(None)
        self.assertIsNone(extracted_text)

    def test_analysis_numeric_years_only(self):
        """Tests analysis when only numeric years are present."""
        
        result = extract_and_analyze_dates(text)
        self.assertListEqual(result['direct_numeric_years'], [1650, 1688, 1720])
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['minimum'], 1650)
        self.assertEqual(result['maximum'], 1720)

    def test_analysis_textual_dates_only(self):
        """Tests analysis when only textual phrases are present."""
        
        text = "Relatos do início do século XVII e de meados do século XVIII."
        result = extract_and_analyze_dates(text)
        
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1630), (1740, 1760)])
        
        self.assertListEqual(result['combined_representative_years'], [1615, 1750])
        self.assertEqual(result['count'], 2)

    def test_analysis_mixed_dates(self):
        """Tests analysis with a mix of numeric years and textual phrases."""

        text = "Aconteceu em 1710, durante a primeira metade do século XVIII, e novamente em 1795."
        result = extract_and_analyze_dates(text)
        self.assertListEqual(result['direct_numeric_years'], [1710, 1795])

        self.assertCountEqual(result['calculated_textual_intervals'], [(1700, 1750)])

        self.assertListEqual(result['combined_representative_years'], [1710, 1725, 1795])
        self.assertEqual(result['count'], 3)

    def test_analysis_full_century(self):
        """Tests analysis when only the century is mentioned."""
        
        text = "Artefatos do século XVII."
        result = extract_and_analyze_dates(text)
        
        self.assertCountEqual(result['calculated_textual_intervals'], [(1600, 1700)])
        
        self.assertListEqual(result['combined_representative_years'], [1650])
        self.assertEqual(result['count'], 1)

    def test_analysis_no_dates(self):
        """Tests analysis behavior when no relevant dates are found."""

        text = "A descriptive text without clear chronological references." 
        result = extract_and_analyze_dates(text)

        self.assertEqual(result['count'], 0)
        self.assertIsNone(result['minimum'])
        self.assertIsNone(result['mean'])

    def test_integration_pdf_to_analysis(self):
        """Tests the full flow: extract text from PDF and analyze it."""

        extracted_text = extract_text_from_pdf(TEST_PDF_FILENAME)
        self.assertIsNotNone(extracted_text)

        result = extract_and_analyze_dates(extracted_text)
        
        self.assertListEqual(result['direct_numeric_years'], [1750])
        self.assertCountEqual(result['calculated_textual_intervals'], [(1700, 1800)])
        
        self.assertListEqual(result['combined_representative_years'], [1750])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['minimum'], 1750)
        self.assertEqual(result['maximum'], 1750)


if __name__ == '__main__':
    suite = unittest.TestSuite()
    
    suite.addTest(unittest.makeSuite(TestDateExtractorWithPDF))
    
    runner = unittest.TextTestRunner(verbosity=2)
    
    runner.run(suite)
