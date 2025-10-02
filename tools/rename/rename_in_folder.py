import os

folder = r"2021/"  # dosyaların bulunduğu klasör
files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]
files.sort()  # sıralama için

for i, old_name in enumerate(files, start=1):
    new_name = f"osos_entegrasyon_oms_2021_2025-07-08_part-{i:02d}_v01.xlsx"
    old_path = os.path.join(folder, old_name)
    new_path = os.path.join(folder, new_name)
    os.rename(old_path, new_path)

print("Yeniden adlandırma tamamlandı!")
