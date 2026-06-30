import os
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEST_PARQUET_PATH = BASE_DIR / "data" / "splits" / "router_dataset_v1_test.parquet"
TRAIN_PARQUET_PATH = BASE_DIR / "data" / "splits" / "router_dataset_v1_train.parquet"
ROUTER_MODEL_PATH = BASE_DIR / "outputs" / "router" / "best_router_model.joblib"
OUT_FILE = BASE_DIR / "outputs" / "router" / "e2e_system_metrics.txt"

def calculate_metrics(y_true, y_pred, costs, name=""):
    valid_labels = ["safe", "controversial", "unsafe"]
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, labels=valid_labels, average="macro", zero_division=0)
    
    unsafe_total = sum(1 for yt in y_true if yt == "unsafe")
    unsafe_correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == "unsafe" and yp == "unsafe")
    unsafe_recall = unsafe_correct / unsafe_total if unsafe_total > 0 else 0
    
    avg_cost = np.mean(costs)
    
    return {
        "Name": name,
        "Accuracy": acc,
        "Macro F1": macro_f1,
        "Unsafe Recall": unsafe_recall,
        "Decision Cost": avg_cost
    }

def main():
    print("🚀 Bắt đầu Đánh giá Hệ thống SafeRoute End-to-End")
    
    if not os.path.exists(TEST_PARQUET_PATH):
        print(f"❌ Không tìm thấy test parquet: {TEST_PARQUET_PATH}")
        return
        
    if not os.path.exists(ROUTER_MODEL_PATH):
        print(f"❌ Không tìm thấy router model: {ROUTER_MODEL_PATH}")
        return
        
    # 1. Load Data
    df_test = pd.read_parquet(TEST_PARQUET_PATH)
    print(f"✅ Đã load {len(df_test)} mẫu test từ Parquet.")
    
    # 2. Load Router
    router_meta = joblib.load(ROUTER_MODEL_PATH)
    router_model = router_meta["model_object"]
    print(f"✅ Đã load Router: {router_meta['model_name']}")
    
    # 3. Router Prediction (Load dynamic feature from metadata)
    feature_used = router_meta.get("features_used", ["hidden"])
    if "hidden" not in feature_used:
        raise ValueError("Pipeline baseline hien tai bat buoc phai chua 'hidden'")
    X = np.stack(df_test['hidden'].values)
    router_preds = router_model.predict(X)
    df_test['router_pred'] = router_preds
    
    # Random Router Baseline
    np.random.seed(42)
    df_test['random_route'] = np.random.randint(0, 2, len(df_test))
    
    # Confidence Threshold Baseline
    best_tau = 0.8
    if 'confidence' in df_test.columns:
        if os.path.exists(TRAIN_PARQUET_PATH):
            df_train = pd.read_parquet(TRAIN_PARQUET_PATH)
            if 'confidence' in df_train.columns:
                print("🔍 Đang sweep ngưỡng confidence tối ưu trên tập Train...")
                best_cost = float('inf')
                for tau in np.arange(0.1, 0.95, 0.05):
                    train_conf_route = np.where(df_train['confidence'] < tau, 1, 0)
                    train_conf_cost = np.where(train_conf_route == 1, df_train['cost4'], df_train['cost06']).mean()
                    if train_conf_cost < best_cost:
                        best_cost = train_conf_cost
                        best_tau = tau
                print(f"🎯 Đã tìm được ngưỡng Confidence Threshold tối ưu: {best_tau:.2f}")
            else:
                print("⚠️ Warning: Tập Train không có cột 'confidence', dùng mặc định tau=0.8")
        else:
            print("⚠️ Warning: Không tìm thấy tập Train, dùng mặc định tau=0.8")
            
        df_test['conf_route'] = np.where(df_test['confidence'] < best_tau, 1, 0)
    else:
        print("⚠️ Warning: Không tìm thấy cột 'confidence' trong tập Test, bỏ qua Confidence Router baseline.")
        df_test['conf_route'] = 0
    
    # 4. End-to-End Prediction
    df_test['e2e_pred'] = np.where(
        df_test['router_pred'] == 1,
        df_test['prediction_large'],
        df_test['prediction_small']
    )
    
    df_test['e2e_cost'] = np.where(
        df_test['router_pred'] == 1,
        df_test['cost4'],
        df_test['cost06']
    )
    
    df_test['random_pred'] = np.where(
        df_test['random_route'] == 1,
        df_test['prediction_large'],
        df_test['prediction_small']
    )
    
    df_test['random_cost'] = np.where(
        df_test['random_route'] == 1,
        df_test['cost4'],
        df_test['cost06']
    )
    
    df_test['conf_pred'] = np.where(
        df_test['conf_route'] == 1,
        df_test['prediction_large'],
        df_test['prediction_small']
    )
    
    df_test['conf_cost'] = np.where(
        df_test['conf_route'] == 1,
        df_test['cost4'],
        df_test['cost06']
    )
    
    # 5. Lấy Labels
    y_true = df_test['gold_label'].values
    y_small = df_test['prediction_small'].values
    y_large = df_test['prediction_large'].values
    y_e2e = df_test['e2e_pred'].values
    y_random = df_test['random_pred'].values
    y_conf = df_test['conf_pred'].values
    
    cost06 = df_test['cost06'].values
    cost4 = df_test['cost4'].values
    cost_e2e = df_test['e2e_cost'].values
    cost_random = df_test['random_cost'].values
    cost_conf = df_test['conf_cost'].values
    
    # Tính Oracle (Upper Bound)
    # Oracle thống nhất theo Cost: Luôn chọn model có Decision Cost thấp hơn.
    # Nếu hai model có Cost bằng nhau, ưu tiên 0.6B để tiết kiệm.
    oracle_route = np.where(cost4 < cost06, 1, 0)
    
    df_test['oracle_pred'] = np.where(
        oracle_route == 1,
        y_large,
        y_small
    )
    
    df_test['oracle_cost'] = np.where(
        oracle_route == 1,
        cost4,
        cost06
    )
    
    y_oracle = df_test['oracle_pred'].values
    oracle_cost = df_test['oracle_cost'].mean()
    
    # 6. Tính toán các Metrics
    metrics_06b = calculate_metrics(y_true, y_small, cost06, "Always 0.6B")
    metrics_8b = calculate_metrics(y_true, y_large, cost4, "Always 8B")
    metrics_conf = calculate_metrics(y_true, y_conf, cost_conf, f"Conf Router (τ={best_tau:.2f})")
    metrics_random = calculate_metrics(y_true, y_random, cost_random, "Random Router")
    metrics_e2e = calculate_metrics(y_true, y_e2e, cost_e2e, "SafeRoute(Ours)")
    metrics_oracle = calculate_metrics(y_true, y_oracle, df_test['oracle_cost'].values, "Oracle Upper Bound")
    
    large_usage = np.mean(router_preds) * 100
    random_usage = np.mean(df_test['random_route']) * 100
    conf_usage = np.mean(df_test['conf_route']) * 100
    
    oracle_gap_abs = metrics_e2e["Decision Cost"] - metrics_oracle["Decision Cost"]
    oracle_gap_pct = (oracle_gap_abs / metrics_oracle["Decision Cost"] * 100) if metrics_oracle["Decision Cost"] > 0 else 0
    
    # 7. In Bảng So sánh cho Luận Văn
    print("\n" + "="*95)
    print("🏆 BẢNG SO SÁNH HỆ THỐNG (DÙNG CHO BÁO CÁO/PAPER) 🏆")
    print("="*95)
    
    header = f"| {'System':<18} | {'Accuracy':<8} | {'Macro F1':<8} | {'Unsafe Recall':<13} | {'Dec. Cost':<9} | {'Large Usage':<11} |"
    print(header)
    print("|" + "-"*20 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*15 + "|" + "-"*11 + "|" + "-"*13 + "|")
    
    def print_row(m, usage):
        acc = f"{m['Accuracy']:.4f}"
        f1 = f"{m['Macro F1']:.4f}"
        rec = f"{m['Unsafe Recall']:.4f}"
        cost = f"{m['Decision Cost']:.3f}"
        use = "Optimal" if m['Name'] == "Oracle Upper Bound" else f"{usage:.1f}%"
        print(f"| {m['Name']:<18} | {acc:<8} | {f1:<8} | {rec:<13} | {cost:<9} | {use:<11} |")
        
    print_row(metrics_06b, 0.0)
    print_row(metrics_8b, 100.0)
    print_row(metrics_conf, conf_usage)
    print_row(metrics_random, random_usage)
    print_row(metrics_e2e, large_usage)
    print_row(metrics_oracle, 0)
    
    print("="*95)
    print(f"🌟 Oracle Gap (Absolute): {oracle_gap_abs:.3f}")
    print(f"🌟 Oracle Gap (%):       {oracle_gap_pct:.1f}%")
    
    # 8. Chi tiết cho SafeRoute
    print("\n" + "="*40)
    print("📊 CHI TIẾT SAFEROUTE (E2E)")
    print("="*40)
    valid_labels = ["safe", "controversial", "unsafe"]
    print(classification_report(y_true, y_e2e, labels=valid_labels, digits=4, zero_division=0))
    print("\nConfusion Matrix (Rows=Gold, Cols=Pred):")
    print(valid_labels)
    print(confusion_matrix(y_true, y_e2e, labels=valid_labels))
    
    # Ghi ra file
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("|" + "-"*20 + "|" + "-"*10 + "|" + "-"*10 + "|" + "-"*15 + "|" + "-"*11 + "|" + "-"*13 + "|\n")
        
        def write_row(m, usage):
            acc = f"{m['Accuracy']:.4f}"
            f1 = f"{m['Macro F1']:.4f}"
            rec = f"{m['Unsafe Recall']:.4f}"
            cost = f"{m['Decision Cost']:.3f}"
            use = "Optimal" if m['Name'] == "Oracle Upper Bound" else f"{usage:.1f}%"
            f.write(f"| {m['Name']:<18} | {acc:<8} | {f1:<8} | {rec:<13} | {cost:<9} | {use:<11} |\n")
            
        write_row(metrics_06b, 0.0)
        write_row(metrics_8b, 100.0)
        write_row(metrics_conf, conf_usage)
        write_row(metrics_random, random_usage)
        write_row(metrics_e2e, large_usage)
        write_row(metrics_oracle, 0)
        
        f.write(f"\nOracle Gap (Absolute): {oracle_gap_abs:.3f}\n")
        f.write(f"Oracle Gap (%):       {oracle_gap_pct:.1f}%\n")
        f.write("\n" + classification_report(y_true, y_e2e, labels=valid_labels, digits=4, zero_division=0) + "\n")
        f.write("\nConfusion Matrix:\n")
        f.write(str(valid_labels) + "\n")
        f.write(str(confusion_matrix(y_true, y_e2e, labels=valid_labels)) + "\n")
        
    print(f"\n✅ Đã lưu kết quả chi tiết tại: {OUT_FILE}")

if __name__ == "__main__":
    main()
