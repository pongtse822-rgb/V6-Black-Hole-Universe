# 宇宙黑洞膜模型模擬研究

## 簡介

本專案旨在研究基於黑洞膜模型的宇宙演化模擬。透過延長模擬時間，我們得以深入分析宇宙的長期行為和關鍵物理指標的演化，包括膨脹動力學、均勻化趨勢、結構形成和邊界膜效應。

## 專案結構

- `code/`:
  - `run_v6.py`: 模擬的主執行腳本。
  - `d.py`: 包含宇宙模擬核心邏輯和參數設置的腳本。
- `input_params/`:
  - (此資料夾預留，若有外部輸入參數文件將放置於此)
- `results/`:
  - `RESULT.txt`: 模擬運行後生成的 JSON 格式結果文件。
  - `plots/`: 包含所有數據可視化圖表 (PNG 格式)。

## 如何運行模擬

### 系統要求

- Python 3.x
- `google.colab` 環境 (或具備相同檔案路徑結構的環境)
- 必要的 Python 函式庫 (例如 `pandas`, `matplotlib`, `seaborn`, `numpy`)

### 環境設置

1.  **掛載 Google Drive**: 由於模擬腳本位於 Google Drive 中，請確保您的 Colab 環境已正確掛載 Google Drive 至 `/content/drive`。

    ```python
    from google.colab import drive
    drive.mount('/content/drive')
    ```

2.  **確保檔案路徑正確**: 本專案假設 `run_v6.py` 和 `d.py` 位於 `/content/drive/MyDrive/experiment/` 路徑下。

### 執行步驟

1.  **配置 `d.py` 中的 `EPOCHS`**: 為了進行延長模擬，我們已將 `d.py` 檔案中的 `EPOCHS` 變數設定為 `20`。這會使模擬實際運行總計 42 個 Epoch (由於模擬內部機制)。

    ```python
    # 範例 (在 d.py 檔案內)
    EPOCHS = 20 # 實際運行總 Epoch 數為 42
    ```

2.  **執行 `run_v6.py`**: 運行主腳本以啟動模擬。該腳本會調用 `d.py` 並生成 `RESULT.txt`。

    ```bash
    !python "/content/drive/MyDrive/experiment/run_v6.py"
    ```

    *注意*: `run_v6.py` 中 `d.py` 的調用路徑已更正為絕對路徑 `"/content/drive/MyDrive/experiment/d.py"`，以避免運行錯誤。

## 結果解釋

模擬結果儲存在 `results/RESULT.txt` 中，為 JSON 格式。該文件包含了多項驗證指標 (T1-T8) 和宇宙的整體狀態摘要。`results/plots/` 資料夾中的圖表提供了這些指標隨時間變化的可視化。

### 關鍵指標

-   **T1: 重力束縛度**: 衡量宇宙中天體的重力束縛程度。
-   **T2: 能量注入 + 物質回收**: 追蹤系統中物質和能量的交換。
-   **T3: 質量守恆**: 驗證模擬中的質量守恆定律。
-   **T4: 均勻化趨勢**: 評估宇宙物質分佈的均勻程度。
-   **T5: 膨脹動力學**: 分析宇宙的膨脹行為 (距離、速率、類型)。
-   **T6: 結構形成**: 記錄天體合併事件和結構複雜化程度。
-   **T7: 束縛演化**: 顯示天體束縛百分比隨時間的變化。
-   **T8: 邊界膜效應**: 觀察宇宙邊界處天體的行為和影響。

## 許可證

(待補充)

## 致謝

(待補充)
