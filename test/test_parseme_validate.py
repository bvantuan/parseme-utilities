#! /usr/bin/env python3

import unittest
from unittest.mock import patch
import sys, os
from io import StringIO

# MWE = 10
# MWE_CATEG = {MWE: {'NotMWE', 'VPC.full', 'IRV', 'MVC', 'VPC.semi', 'VID', 'IAV', 'LVC.full', 'LVC.cause'}}

#to get the current working directory
CURRENT_DIRECTORY = os.getcwd()
os.chdir(CURRENT_DIRECTORY)
TEST_DATA = f'{CURRENT_DIRECTORY}/test/test_data'
DIR_PARSEME_VALIDATE = f'{CURRENT_DIRECTORY}/st-organizers/release-preparation'
# print("DIR_PARSEME_VALIDATE: ", DIR_PARSEME_VALIDATE)
sys.path.append(DIR_PARSEME_VALIDATE)
from parseme_validate import main

class TestFunctionalParsemeValidate(unittest.TestCase):

    def test_functional_validate_mwe_cols(self):
        # The first line doesn't specify global.columns, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train18.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # The first line specifies global.columns but not the column ID, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train19.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # The first line specifies global.columns but not the column PARSEME:MWE, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train20.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # The line specifies global.columns is not the first line, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train32.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Empty value in column PARSEME:MWE, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train21.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # whitespace in column PARSEME:MWE, failed
        test_args = ["--quiet", "--lang", "en", "--level", "1", f"{TEST_DATA}/train22.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)

        # All '*', OK
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train1.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A '_', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train2.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # All '_' for blind version, OK 
        test_args = ["--quiet", "--underspecified_mwes", "--lang", "en", "--level", "2", f"{TEST_DATA}/train3.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A annotation is different '_' for blind version, failed 
        test_args = ["--quiet", "--underspecified_mwes", "--lang", "en", "--level", "2", f"{TEST_DATA}/train7.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # valid MWE codes, OK
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train4.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE code 'a', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train5.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalide MWE code "'1':LVC.cause", failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train33.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE code '1:', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train6.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE category '1:LVC', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train8.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE code '1%LVC.cause', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train9.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE code '1:VID;*;_', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train37.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # An invalid MWE code '*;1', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train38.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A MWE code was repeated '1:LVC.cause' and '1:LVC.cause', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train10.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A MWE code was redefined '1:LVC.cause' and '1:LVC.full', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train11.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A MWE code without giving it a category right away '1', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train12.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # MWE keys do not form a sequence '1,3', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train13.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # mwe interval 1-13(out of range), failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train14.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A multiple token contains only a star "*", OK
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train15.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A multiple token contains a "_", failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train34.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
         # A multiple token contains a "_" for blind version, OK
        test_args = ["--quiet", "--underspecified_mwes", "--lang", "en", "--level", "2", f"{TEST_DATA}/train35.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A multiple token contains a MWE code, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train16.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # A multiple token contains an invalid annotaion 'a' out of a star "*" or an underscore "_", failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train17.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field source_sent_id contains only two parts separated by spaces '# source_sent_id = http://hdl.handle.net/11234/1-4923 email-enronsent17_01-0049', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train23.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field source_sent_id contains three parts separated by semicolons '# source_sent_id = http://hdl.handle.net/11234/1-4923;UD_English-EWT/en_ewt-ud-train.conllu;email-enronsent17_01-0049', failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train24.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field source_sent_id is present twice, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train25.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field source_sent_id is not present, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train36.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # sent_id is not unique, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train26.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field text is present twice, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train27.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field text is not present, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train31.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field text ends with space, failed
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train28.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # NotMWE is allowed for level < 3, OK
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train29.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # NotMWE is not allowed for level >= 3, failed
        test_args = ["--quiet", "--lang", "en", "--level", "3", f"{TEST_DATA}/train29.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field metadata is allowed for level < 3, OK
        test_args = ["--quiet", "--lang", "en", "--level", "2", f"{TEST_DATA}/train30.cupt"]
        expected_exit_code = 0
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        # Field metadata is not allowed for level >= 3, failed
        test_args = ["--quiet", "--lang", "en", "--level", "3", f"{TEST_DATA}/train30.cupt"]
        expected_exit_code = 1
        with patch('sys.argv', ["parseme_validate.py"] + test_args):
            exit_code = main()
            self.assertEqual(exit_code, expected_exit_code)
        
        

if __name__ == "__main__":
    unittest.main()

