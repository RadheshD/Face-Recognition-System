import sys
import os
import torch

backend_dir = r"c:\Users\radhe\OneDrive\Desktop\FRS\Face-Recognition-System\attendance_ai\backend"
sys.path.append(backend_dir)
os.chdir(backend_dir)

from services.anti_spoof_service import MiniFASNet
model = MiniFASNet()

model_path = os.path.join("resources", "anti_spoof", "2.7_80x80_MiniFASNetV2.pth")
state_dict_raw = torch.load(model_path, map_location="cpu")

if "state_dict" in state_dict_raw:
    state_dict = state_dict_raw["state_dict"]
else:
    state_dict = state_dict_raw

print("--- MODEL KEYS ---")
for k in list(model.state_dict().keys())[:10]:
    print(k)
    
print("\n--- STATE DICT KEYS ---")
for k in list(state_dict.keys())[:10]:
    print(k)
    
missing, unexpected = model.load_state_dict(state_dict, strict=False)
print(f"\nMissing keys: {len(missing)}")
print(f"Unexpected keys: {len(unexpected)}")
