"""
Analysis engine for Excel and financial data processing
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import io
import base64

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """Handles data analysis and financial processing"""
    
    def __init__(self):
        self.supported_formats = ['xlsx', 'xls', 'csv']
        self.max_rows = 100000  # Limit for performance
    
    def analyze_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Analyze uploaded file and return insights"""
        try:
            # Determine file type
            file_extension = filename.split('.')[-1].lower()
            
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Load data
            df = self._load_data(file_content, file_extension)
            
            # Perform basic analysis
            analysis_results = {
                'basic_info': self._get_basic_info(df),
                'data_quality': self._assess_data_quality(df),
                'numerical_summary': self._get_numerical_summary(df),
                'categorical_summary': self._get_categorical_summary(df),
                'time_series_analysis': self._analyze_time_series(df),
                'financial_metrics': self._calculate_financial_metrics(df)
            }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            raise
    
    def _load_data(self, file_content: bytes, file_extension: str) -> pd.DataFrame:
        """Load data from file content"""
        try:
            if file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(io.BytesIO(file_content))
            elif file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                raise ValueError(f"Unsupported format: {file_extension}")
            
            # Limit rows for performance
            if len(df) > self.max_rows:
                logger.warning(f"File has {len(df)} rows, limiting to {self.max_rows}")
                df = df.head(self.max_rows)
            
            return df
            
        except Exception as e:
            logger.error(f"Data loading error: {str(e)}")
            raise
    
    def _get_basic_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get basic information about the dataset"""
        return {
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
            'data_types': df.dtypes.astype(str).to_dict(),
            'memory_usage': df.memory_usage(deep=True).sum(),
            'shape': df.shape
        }
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality metrics"""
        total_cells = df.shape[0] * df.shape[1]
        
        quality_metrics = {
            'missing_values': {
                'total_missing': df.isnull().sum().sum(),
                'missing_percentage': (df.isnull().sum().sum() / total_cells) * 100,
                'columns_with_missing': df.columns[df.isnull().any()].tolist(),
                'missing_by_column': df.isnull().sum().to_dict()
            },
            'duplicates': {
                'duplicate_rows': df.duplicated().sum(),
                'duplicate_percentage': (df.duplicated().sum() / len(df)) * 100
            },
            'data_consistency': self._check_data_consistency(df)
        }
        
        return quality_metrics
    
    def _check_data_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check for data consistency issues"""
        consistency_checks = {
            'negative_amounts': 0,
            'future_dates': 0,
            'suspicious_values': []
        }
        
        # Check for potential amount columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if any(keyword in col.lower() for keyword in ['amount', 'value', 'price', 'cost']):
                negative_count = (df[col] < 0).sum()
                consistency_checks['negative_amounts'] += negative_count
        
        # Check for date columns
        date_columns = df.select_dtypes(include=['datetime64']).columns
        for col in date_columns:
            future_dates = (df[col] > datetime.now()).sum()
            consistency_checks['future_dates'] += future_dates
        
        return consistency_checks
    
    def _get_numerical_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics for numerical columns"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {'message': 'No numerical columns found'}
        
        return {
            'summary_statistics': numeric_df.describe().to_dict(),
            'correlation_matrix': numeric_df.corr().to_dict(),
            'outliers': self._detect_outliers(numeric_df)
        }
    
    def _detect_outliers(self, df: pd.DataFrame) -> Dict[str, int]:
        """Detect outliers using IQR method"""
        outliers = {}
        
        for column in df.columns:
            if df[column].dtype in [np.number]:
                Q1 = df[column].quantile(0.25)
                Q3 = df[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_count = ((df[column] < lower_bound) | (df[column] > upper_bound)).sum()
                outliers[column] = int(outlier_count)
        
        return outliers
    
    def _get_categorical_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary for categorical columns"""
        categorical_df = df.select_dtypes(include=['object', 'category'])
        
        if categorical_df.empty:
            return {'message': 'No categorical columns found'}
        
        summary = {}
        for column in categorical_df.columns:
            summary[column] = {
                'unique_values': int(categorical_df[column].nunique()),
                'most_frequent': categorical_df[column].mode().iloc[0] if not categorical_df[column].mode().empty else None,
                'value_counts': categorical_df[column].value_counts().head(10).to_dict()
            }
        
        return summary
    
    def _analyze_time_series(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze time series data if present"""
        date_columns = df.select_dtypes(include=['datetime64']).columns
        
        if date_columns.empty:
            # Try to identify potential date columns
            potential_date_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'modified'])]
            return {'message': f'No datetime columns found. Potential date columns: {potential_date_cols}'}
        
        time_analysis = {}
        for col in date_columns:
            time_analysis[col] = {
                'date_range': {
                    'min_date': df[col].min().isoformat() if pd.notna(df[col].min()) else None,
                    'max_date': df[col].max().isoformat() if pd.notna(df[col].max()) else None,
                    'span_days': (df[col].max() - df[col].min()).days if pd.notna(df[col].min()) and pd.notna(df[col].max()) else None
                },
                'frequency_analysis': self._analyze_date_frequency(df[col])
            }
        
        return time_analysis
    
    def _analyze_date_frequency(self, date_series: pd.Series) -> Dict[str, Any]:
        """Analyze frequency patterns in date series"""
        try:
            # Group by month and year
            date_series = pd.to_datetime(date_series, errors='coerce')
            monthly_counts = date_series.dt.to_period('M').value_counts().sort_index()
            
            return {
                'monthly_distribution': monthly_counts.head(12).to_dict(),
                'most_active_month': str(monthly_counts.idxmax()) if not monthly_counts.empty else None,
                'records_per_month_avg': float(monthly_counts.mean()) if not monthly_counts.empty else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_financial_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate financial metrics if applicable"""
        # Look for common financial columns
        amount_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['amount', 'value', 'price', 'cost', 'balance'])]
        
        if not amount_columns:
            return {'message': 'No financial columns detected'}
        
        financial_metrics = {}
        
        for col in amount_columns:
            if df[col].dtype in [np.number]:
                financial_metrics[col] = {
                    'total': float(df[col].sum()),
                    'average': float(df[col].mean()),
                    'median': float(df[col].median()),
                    'std_deviation': float(df[col].std()),
                    'min_value': float(df[col].min()),
                    'max_value': float(df[col].max()),
                    'positive_count': int((df[col] > 0).sum()),
                    'negative_count': int((df[col] < 0).sum()),
                    'zero_count': int((df[col] == 0).sum())
                }
        
        return financial_metrics
    
    def generate_insights(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate human-readable insights from analysis results"""
        insights = []
        
        # Basic info insights
        basic_info = analysis_results.get('basic_info', {})
        insights.append(f"Dataset contains {basic_info.get('rows', 0):,} rows and {basic_info.get('columns', 0)} columns")
        
        # Data quality insights
        data_quality = analysis_results.get('data_quality', {})
        missing_pct = data_quality.get('missing_values', {}).get('missing_percentage', 0)
        if missing_pct > 10:
            insights.append(f"⚠️ High missing data: {missing_pct:.1f}% of cells are empty")
        
        duplicate_pct = data_quality.get('duplicates', {}).get('duplicate_percentage', 0)
        if duplicate_pct > 5:
            insights.append(f"⚠️ {duplicate_pct:.1f}% of rows are duplicates")
        
        # Financial insights
        financial_metrics = analysis_results.get('financial_metrics', {})
        for col, metrics in financial_metrics.items():
            if isinstance(metrics, dict) and 'total' in metrics:
                total = metrics['total']
                insights.append(f"💰 Total {col}: ${total:,.2f}")
        
        return insights