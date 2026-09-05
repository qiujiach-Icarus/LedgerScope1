import numpy as np
import pandas as pd
from pyod.models.iforest import IForest

class AnomalyMLModel:
    def __init__(self, contamination: float = 0.03, n_estimators: int = 100, random_state: int = 42):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = None
        self.tree_trace = {}

    def fit_predict(self, df: pd.DataFrame, feature_cols: list) -> pd.DataFrame:
        X = df[feature_cols].fillna(0).values
        n_samples = len(df)

        euler_gamma = 0.5772156649
        c_n = (
            2 * (np.log(n_samples - 1) + euler_gamma) - (2 * (n_samples - 1) / n_samples)
            if n_samples > 1
            else 0.0
        )

        self.model = IForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )
        self.model.fit(X)

        split_counts = {col: 0 for col in feature_cols}
        for tree in self.model.detector_.estimators_:
            for f_idx in tree.tree_.feature:
                if f_idx >= 0:
                    split_counts[feature_cols[f_idx]] += 1

        depths = []
        for i in range(n_samples):
            sample = X[i:i+1]
            pl = [tree.decision_path(sample).toarray().sum() - 1 for tree in self.model.detector_.estimators_]
            depths.append(np.mean(pl))
        
        df["平均切分深度"] = np.round(depths, 2)
        raw_scores = self.model.decision_scores_
        s_min, s_max = raw_scores.min(), raw_scores.max()
        if s_max - s_min > 1e-12:
            df["风险评分"] = ((raw_scores - s_min) / (s_max - s_min) * 100).round(2)
        else:
            df["风险评分"] = 0.0
        df["是否异常"] = self.model.labels_

        self.tree_trace = {
            "构建树总数": self.n_estimators,
            "样本容量 n": n_samples,
            "BST期望常数 c(n)": round(c_n, 4),
            "特征维度切分偏好": split_counts,
            "全样本平均隔离深度基准": round(float(np.mean(depths)), 2)
        }

        reasons = []
        for _, row in df.iterrows():
            r = []
            if row.get("amount_deviation_ratio", 1.0) > 2.0:
                r.append("金额远超科目均值")
            if row.get("day_of_week", 0) in [5, 6]:
                r.append("非工作日记账")
            if row.get("month", 0) in [12, 1]:
                r.append("年末/年初突击")
            if not r:
                r.append("多维特征组合离群")
            reasons.append("、".join(r))
        df["异常原因诊断"] = reasons

        return df.sort_values("风险评分", ascending=False).reset_index(drop=True)
