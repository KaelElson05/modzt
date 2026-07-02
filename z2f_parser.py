import os
import zipfile
import json
import shutil
import tempfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any


class Z2FParser:
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.is_valid = self._validate_file()
        
    def _validate_file(self) -> bool:
        """Check if file exists and is a valid zip"""
        if not os.path.exists(self.file_path):
            return False

        if not zipfile.is_zipfile(self.file_path):
            return False

        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                _ = zf.namelist()
            return True
        except (zipfile.BadZipFile, Exception):
            return False
    
    def get_ui_contents(self) -> Optional[Dict[str, str]]:
        if not self.is_valid:
            return None
        
        ui_contents: Dict[str, bytes] = {}
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                ui_files = [f for f in zf.namelist() if f.lower().startswith('ui/')]
                
                if not ui_files:
                    return None
                
                for file_path in ui_files:
                    if not file_path.endswith('/'):
                        try:
                            ui_contents[file_path] = zf.read(file_path)
                        except Exception:
                            pass
            
            return ui_contents if ui_contents else None
        except Exception as e:
            print(f"Error reading z2f file: {e}")
            return None
    
    def list_ui_files(self) -> List[str]:
        if not self.is_valid:
            return []
        
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                ui_files = [f for f in zf.namelist() if f.lower().startswith('ui/') and not f.endswith('/')]
                return ui_files
        except Exception as e:
            print(f"Error listing z2f files: {e}")
            return []
    
    def extract_ui_to_directory(self, output_dir: str) -> bool:
        if not self.is_valid:
            return False
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                for file_path in zf.namelist():
                    if (file_path.startswith('UI/') or file_path.startswith('ui/')) and not file_path.endswith('/'):
                        extracted = zf.extract(file_path, output_dir)
            
            return True
        except Exception as e:
            print(f"Error extracting UI from z2f: {e}")
            return False
    
    def get_all_contents_flat(self) -> Optional[Dict[str, bytes]]:
        if not self.is_valid:
            return None
        
        contents = {}
        try:
            with zipfile.ZipFile(self.file_path, 'r') as zf:
                for file_info in zf.infolist():
                    if not file_info.is_dir():
                        try:
                            contents[file_info.filename] = zf.read(file_info.filename)
                        except Exception:
                            pass
            return contents
        except Exception as e:
            print(f"Error reading all z2f contents: {e}")
            return None
    
    def replace_ui_folder(self, source_archive: str) -> bool:
        if not self.is_valid:
            return False
        
        source_parser = Z2FParser(source_archive)
        if not source_parser.is_valid:
            return False
        
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix='.z2f')
            os.close(temp_fd)
            
            with zipfile.ZipFile(self.file_path, 'r') as zf_source:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED) as zf_temp:
                    for file_info in zf_source.infolist():
                        if not (file_info.filename.startswith('UI/') or file_info.filename.startswith('ui/')):
                            zf_temp.writestr(file_info, zf_source.read(file_info.filename))
            
            with zipfile.ZipFile(source_archive, 'r') as zf_source:
                with zipfile.ZipFile(temp_path, 'a') as zf_temp:
                    for file_info in zf_source.infolist():
                        if (file_info.filename.startswith('UI/') or file_info.filename.startswith('ui/')) and not file_info.is_dir():
                            zf_temp.writestr(file_info, zf_source.read(file_info.filename))
            
            backup_path = self.file_path + '.backup'
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            shutil.copy2(self.file_path, backup_path)
            shutil.move(temp_path, self.file_path)
            
            return True
        except Exception as e:
            print(f"Error replacing UI in archive: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False
    
    def restore_backup(self) -> bool:
        backup_path = self.file_path + '.backup'
        if not os.path.exists(backup_path):
            return False
        
        try:
            shutil.copy2(backup_path, self.file_path)
            return True
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False


class UIManager:
    
    def __init__(self, zt2_path: str):
        self.zt2_path = zt2_path
        self.ui_base_path = os.path.join(zt2_path, "UI")
        self.ui_backup_path = os.path.join(zt2_path, "UI_Backups")
        self.available_uis: Dict[str, str] = {}
        
        os.makedirs(self.ui_backup_path, exist_ok=True)
        self._scan_available_uis()
    
    def _scan_available_uis(self):
        x300_path = os.path.join(self.zt2_path, "x300_000.z2f")
        
        if os.path.exists(x300_path):
            parser = Z2FParser(x300_path)
            if parser.is_valid:
                ui_files = parser.list_ui_files()
                if ui_files:
                    self.available_uis["Default"] = x300_path
    
    def extract_ui_from_archive(self, archive_path: str, ui_name: str) -> bool:
        parser = Z2FParser(archive_path)
        if not parser.is_valid:
            return False
        
        ui_theme_path = os.path.join(self.ui_base_path, ui_name)
        success = parser.extract_ui_to_directory(ui_theme_path)
        
        if success:
            self.available_uis[ui_name] = archive_path
        
        return success
    
    def backup_current_ui(self, backup_name: str = "backup") -> bool:
        if not os.path.exists(self.ui_base_path):
            return False
        
        backup_path = os.path.join(self.ui_backup_path, backup_name)
        try:
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            shutil.copytree(self.ui_base_path, backup_path)
            return True
        except Exception as e:
            print(f"Error backing up UI: {e}")
            return False
    
    def restore_ui_from_backup(self, backup_name: str = "backup") -> bool:
        backup_path = os.path.join(self.ui_backup_path, backup_name)
        if not os.path.exists(backup_path):
            return False
        
        try:
            self.backup_current_ui("pre_restore")
            
            if os.path.exists(self.ui_base_path):
                shutil.rmtree(self.ui_base_path)
            
            shutil.copytree(backup_path, self.ui_base_path)
            return True
        except Exception as e:
            print(f"Error restoring UI: {e}")
            return False
    
    def switch_ui(self, ui_name: str, source_archive: str = None) -> bool:
        if ui_name not in self.available_uis and not source_archive:
            return False
        
        if source_archive is None:
            source_archive = self.available_uis[ui_name]
        
        x302_path = os.path.join(self.zt2_path, "x302_000.z2f")
        
        if not os.path.exists(x302_path):
            print(f"Error: x302_000.z2f not found at {x302_path}")
            return False
        
        parser = Z2FParser(x302_path)
        if not parser.is_valid:
            print("Error: x302_000.z2f is invalid or corrupted")
            return False
        
        success = parser.replace_ui_folder(source_archive)
        
        return success
    
    def get_available_uis(self) -> List[str]:
        return list(self.available_uis.keys())
    
    def list_all_uis_in_mods(self, mods_path: str) -> Dict[str, str]:
        uis = {}
        
        if not os.path.isdir(mods_path):
            return uis
        
        try:
            for root, dirs, files in os.walk(mods_path):
                for file in files:
                    if file.lower().endswith('.z2f'):
                        file_path = os.path.join(root, file)
                        parser = Z2FParser(file_path)
                        
                        if parser.is_valid:
                            ui_files = parser.list_ui_files()
                            if ui_files:
                                ui_name = os.path.splitext(file)[0]
                                uis[ui_name] = file_path
        except Exception as e:
            print(f"Error scanning mods for UI: {e}")
        
        return uis


class UIThemeExtractor:
    
    @staticmethod
    def extract_x300_ui(x300_path: str, output_dir: str) -> Optional[Dict[str, bytes]]:
        parser = Z2FParser(x300_path)
        if not parser.is_valid:
            return None
        
        success = parser.extract_ui_to_directory(output_dir)
        if success:
            return parser.get_ui_contents()
        
        return None
    
    @staticmethod
    def compare_ui_versions(archive1: str, archive2: str) -> Dict[str, bool]:
        parser1 = Z2FParser(archive1)
        parser2 = Z2FParser(archive2)
        
        if not parser1.is_valid or not parser2.is_valid:
            return {"error": "Invalid archive"}
        
        files1 = set(parser1.list_ui_files())
        files2 = set(parser2.list_ui_files())
        
        return {
            "same_files": files1 == files2,
            "only_in_first": list(files1 - files2),
            "only_in_second": list(files2 - files1),
            "common_files": list(files1 & files2)
        }


class CampaignScenarioParser:
    
    CAMPAIGN_PATTERNS = [
        r'scenarios?/campaign',
        r'campaign.*\.xml',
        r'scenarios?/.*\.xml',
        r'maps?/.*\.xml',
        r'world/.*campaign',
    ]
    
    SANDBOX_PATTERNS = [
        r'scenarios?/sandbox',
        r'scenarios?/freeform',
        r'maps?/freeform',
        r'maps?/sandbox',
    ]
    
    def __init__(self, game_path: str):
        self.game_path = game_path
        self.campaigns: List[Dict[str, Any]] = []
        self.scenarios: List[Dict[str, Any]] = []
        self.sandbox_maps: List[Dict[str, Any]] = []
        
    def scan_all_z2f_files(self) -> Dict[str, List[Dict]]:
        results = {
            "campaigns": [],
            "scenarios": [],
            "sandbox_maps": []
        }
        
        if not self.game_path or not os.path.isdir(self.game_path):
            return results
        
        # Scan main directory z2f files
        for filename in os.listdir(self.game_path):
            if filename.lower().endswith('.z2f'):
                full_path = os.path.join(self.game_path, filename)
                file_data = self._scan_z2f_file(full_path)
                self._merge_results(results, file_data)
        
        # Scan xp directory
        xp_dir = os.path.join(self.game_path, "xp")
        if os.path.isdir(xp_dir):
            for filename in os.listdir(xp_dir):
                if filename.lower().endswith('.z2f'):
                    full_path = os.path.join(xp_dir, filename)
                    file_data = self._scan_z2f_file(full_path)
                    self._merge_results(results, file_data)
        
        self.campaigns = results["campaigns"]
        self.scenarios = results["scenarios"]
        self.sandbox_maps = results["sandbox_maps"]
        
        return results
    
    def _scan_z2f_file(self, z2f_path: str) -> Dict[str, List[Dict]]:
        results = {
            "campaigns": [],
            "scenarios": [],
            "sandbox_maps": []
        }
        
        parser = Z2FParser(z2f_path)
        if not parser.is_valid:
            return results
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                namelist = zf.namelist()
                source_name = os.path.basename(z2f_path)
                
                scenario_folders = set()
                map_folders = set()
                folder_xml_files: Dict[str, List[str]] = {}
                
                for entry in namelist:
                    parts = entry.replace('\\', '/').split('/')
                    if len(parts) < 2:
                        continue
                    
                    top = parts[0].lower()
                    folder_name = parts[1]
                    
                    if not folder_name or folder_name.endswith('/'):
                        continue
                    
                    if top == 'scenarios':
                        scenario_folders.add(folder_name)
                        if entry.lower().endswith('.xml') or entry.lower().endswith('.scn') or entry.lower().endswith('.cfg'):
                            folder_xml_files.setdefault(folder_name, []).append(entry)
                    elif top in ('maps', 'map'):
                        map_folders.add(folder_name)
                        if entry.lower().endswith('.xml') or entry.lower().endswith('.cfg'):
                            folder_xml_files.setdefault(folder_name, []).append(entry)
                
                for entry in namelist:
                    entry_lower = entry.lower()
                    if entry_lower.endswith('.xml'):
                        if 'scenario' in entry_lower or 'campaign' in entry_lower:
                            basename = os.path.splitext(os.path.basename(entry))[0]
                            if basename not in scenario_folders:
                                scenario_folders.add(basename)
                                folder_xml_files.setdefault(basename, []).append(entry)
                        elif 'freeform' in entry_lower or 'sandbox' in entry_lower:
                            basename = os.path.splitext(os.path.basename(entry))[0]
                            if basename not in map_folders:
                                map_folders.add(basename)
                                folder_xml_files.setdefault(basename, []).append(entry)
                
                seen_ids = set()
                for folder_name in sorted(scenario_folders):
                    if folder_name in seen_ids:
                        continue
                    seen_ids.add(folder_name)
                    
                    metadata = self._extract_folder_metadata(zf, folder_xml_files.get(folder_name, []))
                    display_name = metadata.get("name") or self._format_name(folder_name)
                    description = metadata.get("description", "")
                    scenario_type = metadata.get("type", "")
                    
                    folder_lower = folder_name.lower()
                    is_campaign = ('campaign' in folder_lower and 'scenario' not in folder_lower)
                    
                    entry_data = {
                        "id": folder_name,
                        "name": display_name,
                        "description": description,
                        "source": source_name,
                        "path": f"scenarios/{folder_name}/",
                        "type": "campaign" if is_campaign else scenario_type or "scenario"
                    }
                    
                    if is_campaign:
                        results["campaigns"].append(entry_data)
                    else:
                        results["scenarios"].append(entry_data)
                
                seen_map_ids = set()
                for folder_name in sorted(map_folders):
                    if folder_name in seen_map_ids:
                        continue
                    seen_map_ids.add(folder_name)
                    
                    metadata = self._extract_folder_metadata(zf, folder_xml_files.get(folder_name, []))
                    
                    results["sandbox_maps"].append({
                        "id": folder_name,
                        "name": metadata.get("name") or self._format_name(folder_name),
                        "size": metadata.get("size", "Unknown"),
                        "biome": metadata.get("biome", "Mixed"),
                        "source": source_name,
                        "path": f"maps/{folder_name}/"
                    })
                            
        except Exception as e:
            print(f"[CampaignParser] Error scanning {z2f_path}: {e}")
        
        return results
    
    def _extract_folder_metadata(self, zf: zipfile.ZipFile, xml_paths: List[str]) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        
        for xml_path in xml_paths:
            try:
                content = zf.read(xml_path).decode('utf-8', errors='ignore')
                
                name_match = re.search(r'<(?:name|title|BFGEntry\s+name=")[^">]*>?([^<"]+)', content, re.IGNORECASE)
                desc_match = re.search(r'<(?:description|desc|info)[^>]*>([^<]+)', content, re.IGNORECASE)
                type_match = re.search(r'<(?:type|mode|gamemode)[^>]*>([^<]+)', content, re.IGNORECASE)
                size_match = re.search(r'<(?:size|mapsize|dimensions|xsize)[^>]*>([^<]+)', content, re.IGNORECASE)
                biome_match = re.search(r'<(?:biome|terrain|biometype)[^>]*>([^<]+)', content, re.IGNORECASE)
                
                if name_match and "name" not in metadata:
                    metadata["name"] = name_match.group(1).strip()
                if desc_match and "description" not in metadata:
                    metadata["description"] = desc_match.group(1).strip()
                if type_match and "type" not in metadata:
                    metadata["type"] = type_match.group(1).strip().lower()
                if size_match and "size" not in metadata:
                    metadata["size"] = size_match.group(1).strip()
                if biome_match and "biome" not in metadata:
                    metadata["biome"] = biome_match.group(1).strip()
                    
            except Exception:
                continue
        
        return metadata
    
    def _parse_scenario_xml(self, content: str, path: str, source: str) -> Optional[Dict]:
        try:
            name_match = re.search(r'<(?:name|title)[^>]*>([^<]+)</(?:name|title)>', content, re.IGNORECASE)
            desc_match = re.search(r'<(?:description|desc)[^>]*>([^<]+)</(?:description|desc)>', content, re.IGNORECASE)
            type_match = re.search(r'<(?:type|mode)[^>]*>([^<]+)</(?:type|mode)>', content, re.IGNORECASE)
            
            scenario_id = os.path.splitext(os.path.basename(path))[0]
            
            return {
                "id": scenario_id,
                "name": name_match.group(1).strip() if name_match else self._format_name(scenario_id),
                "description": desc_match.group(1).strip() if desc_match else "",
                "type": type_match.group(1).strip().lower() if type_match else "scenario",
                "source": source,
                "path": path
            }
        except Exception:
            return None
    
    def _parse_map_xml(self, content: str, path: str, source: str) -> Optional[Dict]:
        try:
            name_match = re.search(r'<(?:name|title)[^>]*>([^<]+)</(?:name|title)>', content, re.IGNORECASE)
            size_match = re.search(r'<(?:size|dimensions)[^>]*>([^<]+)</(?:size|dimensions)>', content, re.IGNORECASE)
            biome_match = re.search(r'<(?:biome|terrain)[^>]*>([^<]+)</(?:biome|terrain)>', content, re.IGNORECASE)
            
            map_id = os.path.splitext(os.path.basename(path))[0]
            
            return {
                "id": map_id,
                "name": name_match.group(1).strip() if name_match else self._format_name(map_id),
                "size": size_match.group(1).strip() if size_match else "Unknown",
                "biome": biome_match.group(1).strip() if biome_match else "Mixed",
                "source": source,
                "path": path
            }
        except Exception:
            return None
    
    def _format_name(self, raw_name: str) -> str:
        name = raw_name.replace("_", " ").replace("-", " ")
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return name.title()
    
    def _merge_results(self, target: Dict, source: Dict):
        for key in ["campaigns", "scenarios", "sandbox_maps"]:
            existing_ids = {item["id"] for item in target[key]}
            for item in source[key]:
                if item["id"] not in existing_ids:
                    target[key].append(item)
                    existing_ids.add(item["id"])
    
    def get_campaigns(self) -> List[Dict]:
        return self.campaigns
    
    def get_scenarios(self) -> List[Dict]:
        return self.scenarios
    
    def get_sandbox_maps(self) -> List[Dict]:
        return self.sandbox_maps


class EarthTextureExtractor:
    
    GLOBE_FOLDER = "UI/globe/"
    
    GLOBE_TEXTURES = [
        "earth_all.dds",
        "earth_TEST.dds",
        "earth_lights.dds",
    ]
    
    BIOME_TEXTURES = {
        "alpine": "Earth_Biome_Alpine.dds",
        "boreal": "Earth_Biome_Boreal.dds",
        "desert": "Earth_Biome_Desert.dds",
        "grassland": "Earth_Biome_Grassland.dds",
        "rainforest": "Earth_Biome_Rainforest.dds",
        "savannah": "Earth_Biome_Savannah.dds",
        "scrub": "Earth_Biome_Scrub.dds",
        "temperate": "Earth_Biome_Temperate.dds",
        "tundra": "Earth_Biome_Tundra.dds",
        "wetlands": "Earth_Biome_Wetlands.dds",
    }
    
    EARTH_TEXTURE_PATTERNS = [
        r'ui/.*earth.*\.(dds|png|bmp|tga)',
        r'ui/.*globe.*\.(dds|png|bmp|tga)',
        r'ui/.*world.*\.(dds|png|bmp|tga)',
        r'ui/.*planet.*\.(dds|png|bmp|tga)',
        r'ui/mainmenu/.*\.(dds|png|bmp|tga)',
        r'ui/.*map.*\.(dds|png|bmp|tga)',
    ]
    
    def __init__(self, game_path: str, cache_dir: str):
        self.game_path = game_path
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def extract_globe_textures(self, z2f_filename: str = "x300_000.z2f") -> Dict[str, str]:
        """Extract all globe textures from the z2f file"""
        z2f_path = os.path.join(self.game_path, z2f_filename)
        extracted = {}
        
        if not os.path.isfile(z2f_path):
            print(f"[GlobeExtractor] File not found: {z2f_path}")
            return extracted
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                namelist = zf.namelist()
                
                for tex_name in self.GLOBE_TEXTURES:
                    tex_path = f"{self.GLOBE_FOLDER}{tex_name}"
                    if tex_path in namelist:
                        cache_path = self._extract_file(zf, tex_path)
                        if cache_path:
                            extracted["earth_main"] = cache_path
                            break
                
                cloud_path = f"{self.GLOBE_FOLDER}clouds.dds"
                if cloud_path in namelist:
                    cache_path = self._extract_file(zf, cloud_path)
                    if cache_path:
                        extracted["clouds"] = cache_path
                
                for biome_name, tex_file in self.BIOME_TEXTURES.items():
                    tex_path = f"{self.GLOBE_FOLDER}{tex_file}"
                    if tex_path in namelist:
                        cache_path = self._extract_file(zf, tex_path)
                        if cache_path:
                            extracted[f"biome_{biome_name}"] = cache_path
                
                for dot_tex in ["mapdot_normal.dds", "mapdot_selected.dds"]:
                    tex_path = f"{self.GLOBE_FOLDER}{dot_tex}"
                    if tex_path in namelist:
                        cache_path = self._extract_file(zf, tex_path)
                        if cache_path:
                            extracted[dot_tex.replace(".dds", "")] = cache_path
                
        except Exception as e:
            print(f"[GlobeExtractor] Error extracting from {z2f_path}: {e}")
        
        return extracted
    
    def _extract_file(self, zf: zipfile.ZipFile, file_path: str) -> Optional[str]:
        cache_name = os.path.basename(file_path).replace(' ', '_')
        cache_path = os.path.join(self.cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            try:
                with zf.open(file_path) as src:
                    with open(cache_path, 'wb') as dst:
                        dst.write(src.read())
                print(f"[GlobeExtractor] Extracted: {file_path} -> {cache_path}")
            except Exception as e:
                print(f"[GlobeExtractor] Failed to extract {file_path}: {e}")
                return None
        
        return cache_path
    
    def convert_dds_to_png(self, dds_path: str) -> Optional[str]:
        if not os.path.isfile(dds_path):
            return None
        
        png_path = dds_path.rsplit('.', 1)[0] + '.png'
        
        if os.path.exists(png_path):
            return png_path
        
        try:
            from PIL import Image
            img = Image.open(dds_path)
            img.save(png_path, 'PNG')
            print(f"[GlobeExtractor] Converted DDS to PNG: {png_path}")
            return png_path
        except Exception as e:
            print(f"[GlobeExtractor] PIL DDS conversion failed: {e}")
        
        try:
            import imageio.v3 as iio
            img_array = iio.imread(dds_path)
            iio.imwrite(png_path, img_array)
            print(f"[GlobeExtractor] Converted DDS via imageio: {png_path}")
            return png_path
        except Exception as e:
            print(f"[GlobeExtractor] imageio DDS conversion failed: {e}")
        
        return None
        
    def extract_earth_texture(self, z2f_filename: str = "x300_000.z2f") -> Optional[str]:
        textures = self.extract_globe_textures(z2f_filename)
        earth_path = textures.get("earth_main")
        
        if earth_path:
            png_path = self.convert_dds_to_png(earth_path)
            return png_path if png_path else earth_path
        
        return None
    
    def list_ui_textures(self, z2f_filename: str = "x302_000.z2f") -> List[Dict[str, str]]:
        z2f_path = os.path.join(self.game_path, z2f_filename)
        textures = []
        
        if not os.path.isfile(z2f_path):
            return textures
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                for entry in zf.namelist():
                    entry_lower = entry.lower()
                    if entry_lower.startswith('ui/') and any(entry_lower.endswith(ext) for ext in ['.dds', '.png', '.bmp', '.tga', '.jpg']):
                        textures.append({
                            "path": entry,
                            "name": os.path.basename(entry),
                            "size": zf.getinfo(entry).file_size
                        })
        except Exception as e:
            print(f"[EarthTexture] Error listing textures: {e}")
        
        return textures
    
    def extract_specific_texture(self, z2f_filename: str, texture_path: str) -> Optional[str]:
        z2f_path = os.path.join(self.game_path, z2f_filename)
        
        if not os.path.isfile(z2f_path):
            return None
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                if texture_path in zf.namelist():
                    cache_name = os.path.basename(texture_path).replace(' ', '_')
                    cache_path = os.path.join(self.cache_dir, cache_name)
                    
                    if not os.path.exists(cache_path):
                        with zf.open(texture_path) as src:
                            with open(cache_path, 'wb') as dst:
                                dst.write(src.read())
                    
                    return cache_path
        except Exception as e:
            print(f"[EarthTexture] Error extracting specific texture: {e}")
        
        return None


class NIFExtractor:
    
    GLOBE_NIF_PATTERNS = [
        "ui/globe/globe.nif",
        "ui/globe/earth.nif", 
        "ui/globe/world.nif",
        "ui/mainmenu/globe.nif",
        "shared/globe/globe.nif",
        "shared/ui/globe.nif",
    ]
    
    def __init__(self, game_path: str, cache_dir: str):
        self.game_path = game_path
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def extract_globe_nif(self, z2f_filename: str = "x300_000.z2f") -> Optional[str]:
        z2f_path = os.path.join(self.game_path, z2f_filename)
        
        if not os.path.isfile(z2f_path):
            print(f"[NIFExtractor] File not found: {z2f_path}")
            return None
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                namelist = zf.namelist()
                namelist_lower = {n.lower(): n for n in namelist}
                
                for pattern in self.GLOBE_NIF_PATTERNS:
                    if pattern in namelist_lower:
                        actual_path = namelist_lower[pattern]
                        return self._extract_file(zf, actual_path)
                
                for name in namelist:
                    name_lower = name.lower()
                    if name_lower.endswith('.nif') and ('globe' in name_lower or 'earth' in name_lower):
                        print(f"[NIFExtractor] Found globe NIF: {name}")
                        return self._extract_file(zf, name)
                
                nif_files = [n for n in namelist if n.lower().endswith('.nif')]
                if nif_files:
                    print(f"[NIFExtractor] Available NIF files: {nif_files[:10]}")
                else:
                    print(f"[NIFExtractor] No NIF files found in {z2f_filename}")
                    
        except Exception as e:
            print(f"[NIFExtractor] Error extracting NIF from {z2f_path}: {e}")
        
        return None
    
    def extract_all_nif_from_path(self, z2f_filename: str, internal_path: str) -> List[str]:
        z2f_path = os.path.join(self.game_path, z2f_filename)
        extracted = []
        
        if not os.path.isfile(z2f_path):
            return extracted
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                for name in zf.namelist():
                    if name.lower().startswith(internal_path.lower()) and name.lower().endswith('.nif'):
                        cache_path = self._extract_file(zf, name)
                        if cache_path:
                            extracted.append(cache_path)
                            
        except Exception as e:
            print(f"[NIFExtractor] Error: {e}")
        
        return extracted
    
    def _extract_file(self, zf: zipfile.ZipFile, file_path: str) -> Optional[str]:
        cache_name = os.path.basename(file_path).replace(' ', '_')
        cache_path = os.path.join(self.cache_dir, cache_name)
        
        if not os.path.exists(cache_path):
            try:
                with zf.open(file_path) as src:
                    with open(cache_path, 'wb') as dst:
                        dst.write(src.read())
                print(f"[NIFExtractor] Extracted: {file_path} -> {cache_path}")
            except Exception as e:
                print(f"[NIFExtractor] Failed to extract {file_path}: {e}")
                return None
        
        return cache_path
    
    def list_nif_files(self, z2f_filename: str = "x300_000.z2f") -> List[Dict[str, str]]:
        z2f_path = os.path.join(self.game_path, z2f_filename)
        nif_files = []
        
        if not os.path.isfile(z2f_path):
            return nif_files
        
        try:
            with zipfile.ZipFile(z2f_path, 'r') as zf:
                for entry in zf.namelist():
                    if entry.lower().endswith('.nif'):
                        nif_files.append({
                            "path": entry,
                            "name": os.path.basename(entry),
                            "size": zf.getinfo(entry).file_size
                        })
        except Exception as e:
            print(f"[NIFExtractor] Error listing NIF files: {e}")
        
        return nif_files
    
    def scan_all_archives_for_globe(self) -> Optional[Tuple[str, str]]:
        if not self.game_path or not os.path.isdir(self.game_path):
            return None
        
        priority_files = ["x300_000.z2f", "x302_000.z2f", "x100_000.z2f", "x000_000.z2f"]
        
        for z2f_name in priority_files:
            z2f_path = os.path.join(self.game_path, z2f_name)
            if os.path.isfile(z2f_path):
                nif_path = self.extract_globe_nif(z2f_name)
                if nif_path:
                    return (z2f_name, nif_path)
        
        for filename in os.listdir(self.game_path):
            if filename.lower().endswith('.z2f') and filename not in priority_files:
                nif_path = self.extract_globe_nif(filename)
                if nif_path:
                    return (filename, nif_path)
        
        xp_dir = os.path.join(self.game_path, "xp")
        if os.path.isdir(xp_dir):
            for filename in os.listdir(xp_dir):
                if filename.lower().endswith('.z2f'):
                    full_path = os.path.join("xp", filename)
                    nif_path = self.extract_globe_nif(full_path)
                    if nif_path:
                        return (full_path, nif_path)
        
        return None


class MapLocationData:

    LOCATIONS = {
        "Africa Campaign": {"lat": 0, "lon": 25, "region": "Africa"},
        "Marine Animals Campaign": {"lat": 25, "lon": -80, "region": "Caribbean"},
        "Marine Shows Campaign": {"lat": 35, "lon": -120, "region": "Pacific"},
        "Endangered Animals Campaign": {"lat": 20, "lon": 100, "region": "Asia"},
        "Photo Safari Campaign": {"lat": -2, "lon": 35, "region": "East Africa"},
        "Transportation Campaign": {"lat": 40, "lon": -100, "region": "North America"},
        "Dinosaur Zoo Campaign": {"lat": 45, "lon": -110, "region": "Montana"},
        "Extinct Animals Campaign": {"lat": 50, "lon": 10, "region": "Europe"},
        "Species Survival": {"lat": -15, "lon": 130, "region": "Australia"},
        "World Campaigns": {"lat": 0, "lon": 0, "region": "Global"},
        "Zookeeper Training": {"lat": 38, "lon": -77, "region": "Washington DC"},
        "Campaign 1": {"lat": 40, "lon": -74, "region": "New York"},
        "Campaign 2": {"lat": 51, "lon": 0, "region": "London"},
    }
    
    BIOME_COLORS = {
        "Savannah": "#C4A269",
        "Tropical Rainforest": "#228B22",
        "Temperate Forest": "#355E3B",
        "Desert": "#EDC9AF",
        "Boreal Forest": "#4A5D23",
        "Alpine": "#87CEEB",
        "Wetlands": "#4682B4",
        "Grassland": "#7CFC00",
        "Coastal": "#00CED1",
        "Tundra": "#DCDCDC",
    }
    
    @classmethod
    def get_location(cls, campaign_name: str) -> Optional[Dict]:
        """Get location data for a campaign"""
        return cls.LOCATIONS.get(campaign_name)
    
    @classmethod
    def get_biome_color(cls, biome_name: str) -> str:
        """Get color for a biome type"""
        return cls.BIOME_COLORS.get(biome_name, "#808080")
