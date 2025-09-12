# modules/bbva/bbva_parser.py - BBVA PDF parser with integrated validation

"""
BBVA PDF parsing engine with integrated validation system
Extracts transaction data from BBVA bank statement PDFs and validates against PDF totals
"""

import pdfplumber
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, InvalidOperation

from .bbva_helpers import BBVAHelpers

class BBVAParser:
    """Main PDF parser for BBVA bank statements with validation"""
    
    def __init__(self):
        self.helpers = BBVAHelpers()
        
    def parse_pdf(self, pdf_path: str) -> Dict:
        """
        Main method to parse a BBVA PDF file with validation
        
        Returns:
            Dict with parsed data, summary, and validation results
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract basic PDF info
                pdf_info = self._extract_pdf_info(pdf)
                pdf_info['file_path'] = pdf_path
                
                # Validate PDF structure
                validation_result = self._validate_pdf_structure(pdf, pdf_info)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'error': validation_result['error'],
                        'file_path': pdf_path
                    }
                
                # Extract transactions with cross-page support
                transactions = self._extract_all_transactions(pdf, pdf_info)
                
                # Generate summary
                summary = self._generate_summary(transactions, pdf_info)
                
                # Validate against PDF totals
                validation = self._validate_against_pdf_totals(transactions)
                
                return {
                    'success': True,
                    'file_path': pdf_path,
                    'pdf_info': pdf_info,
                    'transactions': transactions,
                    'summary': summary,
                    'validation': validation,
                    'parsed_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"PDF parsing failed: {str(e)}",
                'file_path': pdf_path
            }
    
    def _extract_pdf_info(self, pdf) -> Dict:
        """Extract basic information from PDF header with improved text extraction"""
        info = {
            'clabe': None,
            'account_type': None,
            'period_year': None,
            'period_text': '',
            'total_pages': len(pdf.pages)
        }
        
        try:
            # Try multiple text extraction methods
            page_text = None
            first_page = pdf.pages[0]
            
            # Method 1: Standard text extraction
            try:
                page_text = first_page.extract_text()
                if page_text and page_text.strip():
                    print(f"✅ Method 1 (extract_text) worked: {len(page_text)} characters")
                else:
                    page_text = None
            except Exception as e:
                print(f"❌ Method 1 failed: {e}")
            
            # Method 2: Extract text with layout
            if not page_text:
                try:
                    page_text = first_page.extract_text(layout=True)
                    if page_text and page_text.strip():
                        print(f"✅ Method 2 (layout=True) worked: {len(page_text)} characters")
                    else:
                        page_text = None
                except Exception as e:
                    print(f"❌ Method 2 failed: {e}")
            
            # Method 3: Extract words and join
            if not page_text:
                try:
                    words = first_page.extract_words()
                    if words:
                        page_text = ' '.join([word['text'] for word in words])
                        print(f"✅ Method 3 (extract_words) worked: {len(page_text)} characters")
                    else:
                        page_text = None
                except Exception as e:
                    print(f"❌ Method 3 failed: {e}")
            
            # Method 4: Try other pages if first page fails
            if not page_text and len(pdf.pages) > 1:
                try:
                    for page_num in range(1, min(3, len(pdf.pages))):  # Try pages 1 and 2
                        page = pdf.pages[page_num]
                        text = page.extract_text()
                        if text and text.strip():
                            page_text = text
                            print(f"✅ Method 4 (page {page_num}) worked: {len(page_text)} characters")
                            break
                except Exception as e:
                    print(f"❌ Method 4 failed: {e}")
            
            if not page_text or not page_text.strip():
                raise ValueError("Could not extract text from PDF using any method")
            
            print(f"📄 PDF text sample: {page_text[:200]}...")
            
            # Extract CLABE (18-digit numbers)
            clabe_matches = re.findall(r'(\d{18})', page_text)
            print(f"🔍 Found CLABE candidates: {clabe_matches}")
            
            for clabe_candidate in clabe_matches:
                account_type = self.helpers.identify_account_by_clabe(clabe_candidate)
                print(f"🔍 Testing CLABE {clabe_candidate} -> {account_type}")
                if account_type:
                    info['clabe'] = clabe_candidate
                    info['account_type'] = account_type
                    print(f"✅ CLABE matched: {clabe_candidate} = {account_type}")
                    break
            
            # Extract period information with more flexible patterns
            period_patterns = [
                r'Periodo\s+DEL\s+(\d{1,2}/\d{1,2}/\d{4})\s+AL\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'DEL\s+(\d{1,2}/\d{1,2}/\d{4})\s+AL\s+(\d{1,2}/\d{1,2}/\d{4})',
                r'Periodo.*?(\d{1,2}/\d{1,2}/\d{4}).*?(\d{1,2}/\d{1,2}/\d{4})',
            ]
            
            for pattern in period_patterns:
                period_match = re.search(pattern, page_text, re.IGNORECASE)
                if period_match:
                    info['period_text'] = f"DEL {period_match.group(1)} AL {period_match.group(2)}"
                    info['period_year'] = self.helpers.extract_period_year(info['period_text'])
                    print(f"✅ Period matched: {info['period_text']} -> {info['period_year']}")
                    break
            
            print(f"📊 Final extracted info: {info}")
            
        except Exception as e:
            print(f"Warning: Could not extract PDF info: {e}")
            # Print more detailed error info
            import traceback
            print(f"Detailed error: {traceback.format_exc()}")
        
        return info
    
    def _validate_pdf_structure(self, pdf, pdf_info: Dict) -> Dict:
        """Validate that PDF has expected BBVA structure"""
        
        if not pdf_info.get('account_type'):
            if not pdf_info.get('clabe'):
                return {
                    'valid': False,
                    'error': 'Could not find CLABE number in PDF'
                }
            else:
                return {
                    'valid': False,
                    'error': f"Unknown CLABE number: {pdf_info['clabe']}"
                }
        
        if not pdf_info.get('period_year'):
            return {
                'valid': False,
                'error': 'Could not extract period year from PDF'
            }
        
        return {'valid': True}
    
    def _extract_all_transactions(self, pdf, pdf_info: Dict) -> List[Dict]:
        """Extract all transactions from all pages with cross-page support"""
        all_transactions = []
        current_transaction = None
        
        for page_num, page in enumerate(pdf.pages, 1):
            page_transactions, current_transaction = self._extract_page_transactions(
                page, pdf_info, page_num, current_transaction
            )
            all_transactions.extend(page_transactions)
        
        # Save final transaction if exists
        if current_transaction:
            all_transactions.append(current_transaction)
        
        # Sort by date
        all_transactions.sort(key=lambda x: self._date_sort_key(x.get('date', '')))
        
        return all_transactions
    
    def _extract_page_transactions(self, page, pdf_info: Dict, page_num: int, 
                                 continuing_transaction=None) -> tuple:
        """Extract transactions from a single page with cross-page support"""
        transactions = []
        current_transaction = continuing_transaction
        
        try:
            text = page.extract_text()
            if not text:
                return transactions, current_transaction
            
            lines = text.split('\n')
            in_transaction_section = bool(current_transaction)
            found_header_on_this_page = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Check for transaction header
                if self._is_transaction_header(line):
                    in_transaction_section = True
                    found_header_on_this_page = True
                    continue
                
                # Check for footer (stop processing)
                if self._is_footer_line(line):
                    break
                
                # Check for summary (end transactions and extract totals)
                if self._is_summary_line(line):
                    if current_transaction:
                        transactions.append(current_transaction)
                        current_transaction = None
                    
                    # Extract validation totals
                    summary_totals = self._extract_summary_totals(lines[i:])
                    if summary_totals:
                        setattr(self, '_pdf_summary_totals', summary_totals)
                    break
                
                if in_transaction_section:
                    # Wait for header if continuing transaction from previous page
                    if current_transaction and not found_header_on_this_page and page_num > 1:
                        continue
                    
                    # Check for new transaction
                    if self._is_transaction_start(line):
                        if current_transaction:
                            transactions.append(current_transaction)
                        current_transaction = self._parse_transaction_line(line, pdf_info, page_num)
                    
                    # Add to description if current transaction exists
                    elif current_transaction and not self._should_skip_line(line):
                        if self._looks_like_missed_transaction(line):
                            transactions.append(current_transaction)
                            current_transaction = self._parse_transaction_line(line, pdf_info, page_num)
                        else:
                            current_transaction['description'] += f"\n{line}"
            
        except Exception as e:
            print(f"Error processing page {page_num}: {e}")
        
        return transactions, current_transaction
    
    def _is_transaction_header(self, line: str) -> bool:
        """Check if line is the transaction table header"""
        line_upper = line.upper()
        return ('OPER' in line_upper and 'LIQ' in line_upper and 
                'COD' in line_upper and 'DESCRIPCIÓN' in line_upper)
    
    def _is_footer_line(self, line: str) -> bool:
        """Check if line is part of the footer"""
        footer_keywords = [
            'Estimado Cliente', 'Su Estado de Cuenta ha sido modificado',
            'También le informamos', 'Con BBVA adelante', 'La GAT Real',
            'BBVA MEXICO, S.A.', 'Av. Paseo de la Reforma', 'R.F.C.'
        ]
        return any(keyword in line for keyword in footer_keywords)
    
    def _is_summary_line(self, line: str) -> bool:
        """Check if line is part of transaction summary"""
        summary_keywords = [
            'Total de Movimientos', 'TOTAL IMPORTE CARGOS', 'TOTAL IMPORTE ABONOS',
            'SALDO INICIAL', 'SALDO FINAL', 'TOTAL DE CARGOS', 'TOTAL DE ABONOS'
        ]
        return any(keyword in line for keyword in summary_keywords)
    
    def _is_transaction_start(self, line: str) -> bool:
        """Check if line starts a new transaction"""
        return bool(re.match(r'^(\d{1,2}/[A-Z]{3})\s+(\d{1,2}/[A-Z]{3})\s+([A-Z]+\d+)', line))
    
    def _looks_like_missed_transaction(self, line: str) -> bool:
        """Check if line looks like a missed transaction"""
        return bool(re.match(r'^(\d{1,2}/[A-Z]{3})\s+(\d{1,2}/[A-Z]{3})\s+([A-Z]+\d+)', line))
    
    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped"""
        skip_patterns = [
            r'^\d+/\d+$', r'^PAGINA\s+\d+', r'^[A-Z]{3}\s+\d{4}$',
            r'^Estado de Cuenta', r'^MAESTRA PYME BBVA'
        ]
        return any(re.match(pattern, line, re.IGNORECASE) for pattern in skip_patterns)
    
    def _parse_transaction_line(self, line: str, pdf_info: Dict, page_num: int) -> Optional[Dict]:
        """Parse a single transaction line"""
        try:
            match = re.match(r'^(\d{1,2}/[A-Z]{3})\s+(\d{1,2}/[A-Z]{3})\s+([A-Z]+\d+)\s+(.*)', line)
            if not match:
                return None
            
            fecha_oper = match.group(1)
            fecha_liq = match.group(2)
            codigo = match.group(3)
            rest_of_line = match.group(4)
            
            # Store for classification
            self._current_transaction_code = codigo
            self._current_raw_line = line
            
            # Convert dates
            year = pdf_info.get('period_year', datetime.now().year)
            date_converted = self.helpers.convert_spanish_date(fecha_oper, year)
            date_liq_converted = self.helpers.convert_spanish_date(fecha_liq, year)
            
            # Extract amounts and description
            amounts = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', rest_of_line)
            
            description = rest_of_line
            for amount in reversed(amounts):
                last_pos = description.rfind(amount)
                if last_pos != -1:
                    description = description[:last_pos] + description[last_pos + len(amount):]
            description = re.sub(r'\s+', ' ', description).strip()
            
            # Classify transaction
            cargo, abono = self._classify_transaction(description, amounts)
            
            # Parse balances
            saldo = 0.0
            saldo_liq = 0.0
            if len(amounts) >= 2:
                parsed_amounts = [self._parse_amount(amt) for amt in amounts]
                if len(parsed_amounts) >= 3:
                    saldo = parsed_amounts[-2]
                    saldo_liq = parsed_amounts[-1]
                elif len(parsed_amounts) == 2:
                    saldo = parsed_amounts[-1]
                    saldo_liq = saldo
            
            transaction = {
                'date': date_converted,
                'date_liq': date_liq_converted,
                'code': codigo,
                'description': description,
                'cargo': cargo,
                'abono': abono,
                'saldo': saldo,
                'saldo_liq': saldo_liq,
                'file_source': pdf_info.get('file_path', '').split('/')[-1] if pdf_info.get('file_path') else '',
                'page_number': page_num,
                'raw_line': line
            }
            
            # Clean up temporary variables
            if hasattr(self, '_current_transaction_code'):
                delattr(self, '_current_transaction_code')
            if hasattr(self, '_current_raw_line'):
                delattr(self, '_current_raw_line')
            
            return transaction
            
        except Exception as e:
            return None

    # Fixed _classify_transaction method - TRASPASO Logic Corrected
    # Replace the existing method in bbva_parser.py

    def _classify_transaction(self, description: str, amounts: List[str]) -> tuple:
        """Classify transaction as cargo or abono based on transaction code and description"""
        cargo = 0.0
        abono = 0.0
        
        if not amounts:
            return cargo, abono
        
        main_amount = self._parse_amount(amounts[0])
        code = getattr(self, '_current_transaction_code', '')
        desc_upper = description.upper()
        
        # DEBUG: Log all transaction codes and amounts for analysis
        print(f"🔍 CLASSIFYING: Code={code}, Amount=${main_amount}, Desc='{desc_upper[:50]}...'")
        
        # BBVA-specific transaction code rules (HIGHEST PRIORITY)
        if code:
            # ABONO (Credit) transaction codes - EXPANDED LIST
            if code in ['T20', 'W42', 'E57', 'D01', 'D02', 'D03', 'T21', 'T22', 'W40', 'W41', 'W43', 'D04', 'D05']:
                print(f"🟢 ABONO CODE DETECTED: {code}")
                
                # Special handling for W42 TRASPASO
                if code == 'W42':
                    print(f"🔍 W42 TRASPASO DETECTED - Analyzing direction...")
                    
                    # FIXED: Check for OUTGOING keywords first, then default to INCOMING
                    outgoing_keywords = [
                        'ENVIADO', 'SALIDA', 'PAGO A', 'TRANSFERENCIA A', 
                        'TRASPASO A TERCEROS', 'DEBITO', 'CARGO'
                    ]
                    
                    incoming_keywords = [
                        'RECIBIDO', 'INGRESO', 'CAPITAL', 'SAMX', 'BMRCASH',
                        'CREDITO', 'ABONO', 'ENTRADA'
                    ]
                    
                    is_outgoing = any(keyword in desc_upper for keyword in outgoing_keywords)
                    is_incoming = any(keyword in desc_upper for keyword in incoming_keywords)
                    
                    if is_outgoing:
                        cargo = main_amount
                        print(f"🔴 W42 TRASPASO OUTGOING (has outgoing keywords): ${cargo}")
                    elif is_incoming:
                        abono = main_amount
                        print(f"✅ W42 TRASPASO INCOMING (has incoming keywords): ${abono}")
                    else:
                        # DEFAULT: If no clear direction indicators, classify as ABONO
                        # This is because W42 is primarily used for incoming transfers in BBVA
                        abono = main_amount
                        print(f"✅ W42 TRASPASO DEFAULT TO INCOMING: ${abono}")
                    
                    return cargo, abono
                    
                # T20 = SPEI RECIBIDO (always incoming)
                elif code == 'T20':
                    if 'RECIBIDO' in desc_upper or 'INGRESO' in desc_upper:
                        abono = main_amount
                        print(f"✅ T20 SPEI RECIBIDO CLASSIFIED AS ABONO: ${abono}")
                    else:
                        # T20 should always be ABONO, even without RECIBIDO keyword
                        abono = main_amount
                        print(f"✅ T20 DEFAULT TO ABONO: ${abono}")
                    return cargo, abono
                    
                # Other ABONO codes
                else:
                    abono = main_amount
                    print(f"✅ {code} CLASSIFIED AS ABONO: ${abono}")
                    return cargo, abono
                    
            # CARGO (Debit) transaction codes  
            elif code in ['C49', 'C50', 'W83', 'W84', 'W85', 'W86', 'T17', 'E62']:
                cargo = main_amount
                print(f"🔴 {code} CLASSIFIED AS CARGO: ${cargo}")
                return cargo, abono
            else:
                print(f"⚠️ UNKNOWN CODE: {code} - Will use description-based classification")
        
        # Description-based classification (SECONDARY)
        abono_keywords = [
            'ABONO', 'DEPOSITO', 'INGRESO', 'RECIBIDO', 'RECIBIDA',
            'TRANSFERENCIA RECIBIDA', 'DEVOLUCION', 'SPEI RECIBIDO',
            'CREDITO', 'ENTRADA', 'PAGO RECIBIDO'
        ]
        
        cargo_keywords = [
            'PAGO', 'RETIRO', 'COMISION', 'ENVIADO', 'CARGO', 
            'SPEI ENVIADO', 'TRASPASO A TERCEROS', 'PENALIZ',
            'IVA', 'COM TRANSACCIONES', 'COM SERV', 'DEBITO', 'SALIDA'
        ]
        
        # Check for specific ABONO patterns first
        abono_match = any(keyword in desc_upper for keyword in abono_keywords)
        cargo_match = any(keyword in desc_upper for keyword in cargo_keywords)
        
        if abono_match:
            abono = main_amount
            print(f"✅ DESCRIPTION-BASED ABONO: ${abono}")
        elif cargo_match:
            cargo = main_amount
            print(f"🔴 DESCRIPTION-BASED CARGO: ${cargo}")
        else:
            # Default classification
            print(f"⚠️ NO KEYWORDS MATCHED - DEFAULTING TO CARGO: ${main_amount}")
            cargo = main_amount
        
        return cargo, abono

    def _parse_amount(self, amount_str: str) -> float:
        """Parse amount string to float"""
        if not amount_str:
            return 0.0
        
        try:
            cleaned = re.sub(r'[^\d,.\-]', '', str(amount_str))
            if not cleaned or cleaned in ['-', '.', ',']:
                return 0.0
            
            if ',' in cleaned and '.' not in cleaned:
                parts = cleaned.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            elif ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
        except:
            return 0.0
    
    def _date_sort_key(self, date_str: str) -> str:
        """Create sortable key from date string"""
        try:
            parts = date_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}{parts[0].zfill(2)}{parts[1].zfill(2)}"
        except:
            pass
        return date_str
    
    def _extract_summary_totals(self, summary_lines: List[str]) -> Optional[Dict]:
        """Extract totals from summary section for validation"""
        totals = {}
        
        try:
            for line in summary_lines[:10]:
                line = line.strip()
                
                cargo_match = re.search(r'TOTAL\s+IMPORTE\s+CARGOS\s+([\d,]+\.?\d*)\s+TOTAL\s+MOVIMIENTOS\s+CARGOS\s+(\d+)', line)
                if cargo_match:
                    totals['cargo_amount'] = self._parse_amount(cargo_match.group(1))
                    totals['cargo_count'] = int(cargo_match.group(2))
                
                abono_match = re.search(r'TOTAL\s+IMPORTE\s+ABONOS\s+([\d,]+\.?\d*)\s+TOTAL\s+MOVIMIENTOS\s+ABONOS\s+(\d+)', line)
                if abono_match:
                    totals['abono_amount'] = self._parse_amount(abono_match.group(1))
                    totals['abono_count'] = int(abono_match.group(2))
                
                if 'cargo_amount' in totals and 'abono_amount' in totals:
                    break
            
            return totals if totals else None
        except:
            return None
    
    def _validate_against_pdf_totals(self, transactions: List[Dict]) -> Dict:
        """Validate parsed transactions against PDF summary totals"""
        validation = {
            'totals_found': False,
            'cargo_amount_match': False,
            'cargo_count_match': False,
            'abono_amount_match': False,
            'abono_count_match': False,
            'overall_valid': False,
            'discrepancies': [],
            'pdf_totals': {},
            'parsed_totals': {}
        }
        
        # Check if we have PDF totals
        if not hasattr(self, '_pdf_summary_totals'):
            validation['discrepancies'].append("PDF summary totals not found - cannot validate")
            return validation
        
        pdf_totals = self._pdf_summary_totals
        validation['totals_found'] = True
        validation['pdf_totals'] = pdf_totals
        
        # Calculate parsed totals
        cargo_transactions = [t for t in transactions if t.get('cargo', 0) > 0]
        abono_transactions = [t for t in transactions if t.get('abono', 0) > 0]
        
        parsed_cargo_amount = sum(t.get('cargo', 0) for t in transactions)
        parsed_cargo_count = len(cargo_transactions)
        parsed_abono_amount = sum(t.get('abono', 0) for t in transactions)
        parsed_abono_count = len(abono_transactions)
        
        validation['parsed_totals'] = {
            'cargo_amount': parsed_cargo_amount,
            'cargo_count': parsed_cargo_count,
            'abono_amount': parsed_abono_amount,
            'abono_count': parsed_abono_count
        }
        
        # Validate amounts (allow small rounding differences)
        cargo_amount_diff = abs(parsed_cargo_amount - pdf_totals.get('cargo_amount', 0))
        validation['cargo_amount_match'] = cargo_amount_diff < 0.01
        if not validation['cargo_amount_match']:
            validation['discrepancies'].append({
                'type': 'cargo_amount',
                'pdf_value': pdf_totals.get('cargo_amount', 0),
                'parsed_value': parsed_cargo_amount,
                'difference': cargo_amount_diff
            })
        
        # Validate counts
        validation['cargo_count_match'] = parsed_cargo_count == pdf_totals.get('cargo_count', 0)
        if not validation['cargo_count_match']:
            validation['discrepancies'].append({
                'type': 'cargo_count',
                'pdf_value': pdf_totals.get('cargo_count', 0),
                'parsed_value': parsed_cargo_count,
                'difference': abs(parsed_cargo_count - pdf_totals.get('cargo_count', 0))
            })
        
        abono_amount_diff = abs(parsed_abono_amount - pdf_totals.get('abono_amount', 0))
        validation['abono_amount_match'] = abono_amount_diff < 0.01
        if not validation['abono_amount_match']:
            validation['discrepancies'].append({
                'type': 'abono_amount',
                'pdf_value': pdf_totals.get('abono_amount', 0),
                'parsed_value': parsed_abono_amount,
                'difference': abono_amount_diff
            })
        
        validation['abono_count_match'] = parsed_abono_count == pdf_totals.get('abono_count', 0)
        if not validation['abono_count_match']:
            validation['discrepancies'].append({
                'type': 'abono_count',
                'pdf_value': pdf_totals.get('abono_count', 0),
                'parsed_value': parsed_abono_count,
                'difference': abs(parsed_abono_count - pdf_totals.get('abono_count', 0))
            })
        
        # Overall validation
        validation['overall_valid'] = (validation['cargo_amount_match'] and 
                                     validation['cargo_count_match'] and
                                     validation['abono_amount_match'] and 
                                     validation['abono_count_match'])
        
        # Clean up
        if hasattr(self, '_pdf_summary_totals'):
            delattr(self, '_pdf_summary_totals')
        
        return validation
    
    def _generate_summary(self, transactions: List[Dict], pdf_info: Dict) -> Dict:
        """Generate summary statistics for the parsed data"""
        if not transactions:
            return {
                'total_transactions': 0,
                'total_cargos': 0.0,
                'total_abonos': 0.0,
                'net_movement': 0.0,
                'date_range': {'start': None, 'end': None},
                'account_info': pdf_info
            }
        
        total_cargos = sum(t.get('cargo', 0) for t in transactions)
        total_abonos = sum(t.get('abono', 0) for t in transactions)
        
        dates = [t['date'] for t in transactions if t.get('date')]
        date_range = {
            'start': min(dates) if dates else None,
            'end': max(dates) if dates else None
        }
        
        return {
            'total_transactions': len(transactions),
            'total_cargos': round(total_cargos, 2),
            'total_abonos': round(total_abonos, 2),
            'net_movement': round(total_abonos - total_cargos, 2),
            'date_range': date_range,
            'account_info': pdf_info
        }


# Validation helper functions for UI integration
def format_validation_message(validation_result: Dict) -> str:
    """Format validation result for user display"""
    if not validation_result.get('totals_found'):
        return "⚠️ Could not validate - PDF summary totals not found"
    
    if validation_result.get('overall_valid'):
        return "✅ Validation passed - All totals match PDF summary"
    
    discrepancies = validation_result.get('discrepancies', [])
    if not discrepancies:
        return "❓ Validation status unclear"
    
    message = f"❌ Validation failed - {len(discrepancies)} discrepancies found:\n"
    for disc in discrepancies:
        if isinstance(disc, dict):
            disc_type = disc.get('type', 'unknown')
            pdf_val = disc.get('pdf_value', 0)
            parsed_val = disc.get('parsed_value', 0)
            
            if 'amount' in disc_type:
                message += f"• {disc_type.replace('_', ' ').title()}: PDF=${pdf_val:,.2f}, Parsed=${parsed_val:,.2f}\n"
            else:
                message += f"• {disc_type.replace('_', ' ').title()}: PDF={pdf_val}, Parsed={parsed_val}\n"
        else:
            message += f"• {disc}\n"
    
    return message.strip()

def get_validation_status(validation_result: Dict) -> str:
    """Get simple validation status for UI indicators"""
    if not validation_result.get('totals_found'):
        return "unknown"
    
    if validation_result.get('overall_valid'):
        return "valid"
    
    return "invalid"