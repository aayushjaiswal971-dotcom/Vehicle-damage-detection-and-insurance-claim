import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import lightgbm as lgb
import xgboost as xgb
import os

def generate_synthetic_training_data(n_samples=1000):
    """
    Generate synthetic training data for severity and cost models
    """
    np.random.seed(42)
    
    # Generate features
    data = {
        'total_bbox_area': np.random.uniform(1000, 50000, n_samples),
        'max_bbox_area': np.random.uniform(500, 30000, n_samples),
        'num_detections': np.random.randint(1, 5, n_samples),
        'avg_confidence': np.random.uniform(0.5, 0.99, n_samples),
        'total_mask_area': np.random.uniform(500, 40000, n_samples),
        'max_mask_area': np.random.uniform(300, 25000, n_samples),
        'num_masks': np.random.randint(1, 5, n_samples),
        'avg_irregularity': np.random.uniform(1.0, 3.0, n_samples),
        'damage_ratio': np.random.uniform(0.01, 0.3, n_samples),
        'mean_intensity': np.random.uniform(80, 180, n_samples),
        'std_intensity': np.random.uniform(20, 60, n_samples),
        'edge_density': np.random.uniform(0.05, 0.25, n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Generate severity labels based on damage_ratio
    def get_severity(ratio):
        if ratio < 0.05:
            return 'Minor'
        elif ratio < 0.15:
            return 'Moderate'
        else:
            return 'Severe'
    
    df['severity'] = df['damage_ratio'].apply(get_severity)
    
    # Generate cost based on severity and features
    def get_cost(row):
        base_costs = {'Minor': 10000, 'Moderate': 30000, 'Severe': 70000}
        base = base_costs[row['severity']]
        
        # Add variation based on features
        variation = (
            row['damage_ratio'] * 50000 +
            row['num_detections'] * 5000 +
            row['avg_irregularity'] * 3000
        )
        
        cost = base + variation + np.random.normal(0, 5000)
        return max(cost, 5000)
    
    df['cost'] = df.apply(get_cost, axis=1)
    
    return df

def train_severity_model(df):
    """
    Train LightGBM severity classification model
    """
    print("Training severity classification model...")
    
    # Prepare data
    feature_cols = [
        'total_bbox_area', 'max_bbox_area', 'num_detections', 'avg_confidence',
        'total_mask_area', 'max_mask_area', 'num_masks', 'avg_irregularity',
        'damage_ratio', 'mean_intensity', 'std_intensity', 'edge_density'
    ]
    
    X = df[feature_cols].values
    y = df['severity'].values
    
    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    
    # Create LightGBM dataset
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
    
    # Parameters
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'metric': 'multi_logloss',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'verbose': -1
    }
    
    # Train model
    model = lgb.train(
        params,
        train_data,
        num_boost_round=100,
        valid_sets=[test_data],
        callbacks=[lgb.early_stopping(stopping_rounds=10)]
    )
    
    # Save model
    os.makedirs('models', exist_ok=True)
    model.save_model('models/severity_lgb.txt')
    
    # Evaluate
    y_pred = np.argmax(model.predict(X_test), axis=1)
    accuracy = np.mean(y_pred == y_test)
    
    print(f"Severity model accuracy: {accuracy:.4f}")
    print("Model saved to models/severity_lgb.txt")
    
    return model

def train_cost_model(df):
    """
    Train XGBoost cost regression model
    """
    print("\nTraining cost regression model...")
    
    # Prepare data
    feature_cols = [
        'total_bbox_area', 'max_bbox_area', 'num_detections', 'avg_confidence',
        'total_mask_area', 'max_mask_area', 'num_masks', 'avg_irregularity',
        'damage_ratio', 'mean_intensity', 'std_intensity', 'edge_density'
    ]
    
    X = df[feature_cols].values
    y = df['cost'].values
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Create DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dtest = xgb.DMatrix(X_test, label=y_test)
    
    # Parameters
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'eval_metric': 'rmse'
    }
    
    # Train model
    evals = [(dtrain, 'train'), (dtest, 'test')]
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=100,
        evals=evals,
        early_stopping_rounds=10,
        verbose_eval=False
    )
    
    # Save model
    model.save_model('models/cost_xgb.json')
    
    # Evaluate
    y_pred = model.predict(dtest)
    rmse = np.sqrt(np.mean((y_pred - y_test) ** 2))
    mae = np.mean(np.abs(y_pred - y_test))
    
    print(f"Cost model RMSE: ₹{rmse:.2f}")
    print(f"Cost model MAE: ₹{mae:.2f}")
    print("Model saved to models/cost_xgb.json")
    
    return model

def main():
    """
    Main training pipeline
    """
    print("Generating synthetic training data...")
    df = generate_synthetic_training_data(n_samples=2000)
    
    print(f"\nDataset shape: {df.shape}")
    print(f"Severity distribution:\n{df['severity'].value_counts()}")
    print(f"\nCost statistics:\n{df['cost'].describe()}")
    
    # Train models
    severity_model = train_severity_model(df)
    cost_model = train_cost_model(df)
    
    print("\n" + "="*50)
    print("Training completed successfully!")
    print("="*50)
    print("\nTrained models:")
    print("1. models/severity_lgb.txt - Severity classification")
    print("2. models/cost_xgb.json - Cost regression")
    print("\nNote: For production use, train on real labeled data")

if __name__ == '__main__':
    main()
