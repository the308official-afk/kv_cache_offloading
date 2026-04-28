import hashlib
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional

import torch

from sglang.srt.mem_cache.memory_pool_host import HostKVCache

logger = logging.getLogger(__name__)

################################################## CHANGE STRIP ######################################################################
import sys
import time

hicache_storage__debug__nodetokenids_h2s=0 # CHECK_POINT***(sergey's experiments)---
hicache_storage__debug__nodetokenids_s2h=1 # CHECK_POINT***(sergey's experiments)---
hicache_storage__debug__nodetext=0 # CHECK_POINT***

hicache_storage__debug=0
hicache_storage__debug__indices=0 # CHECK_POINT***
hicache_storage__debug__bandwidth_h2s=0 # CHECK_POINT***(my experiments)(sergey's experiments)---
hicache_storage__debug__bandwidth_s2h=1 # CHECK_POINT***(my experiments)(sergey's experiments)---
hicache_storage__debug__enforecethrottling=0 # CHECK_POINT***(my experiments)

SKIP_PRINT_FREQ=1 # 100
# storage bandwidths
LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH=20
LINK_CHANNEL_THRESHOLD_MB___PREFETCH=20

from datetime import datetime
def tprint(*args, **kwargs):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # Include milliseconds
    print(f"[{ts}]", *args, **kwargs)
    sys.stdout.flush() 
    
host_storage_transfer_counter=0
storage_host_transfer_counter=0
total_sleep_time_h2s_ms=0
total_sleep_time_s2h_ms=0
total_data_transferred_h2s=0
total_data_transferred_s2h=0
################################################## CHANGE STRIP ######################################################################

################################################## CHANGE STRIP ######################################################################
# --- traffic_logger.py style snippet (paste into memory_pool_host.py) ---
import os, time, threading
from collections import deque

TRAFFIC_LOG = os.environ.get("SGLANG_TRAFFIC_LOG", "/tmp/sglang_traffic.csv")
BUF_MAX = int(os.environ.get("SGLANG_TRAFFIC_FLUSH_EVERY", "256"))
_buf = deque()
_lock = threading.Lock()

def record_transfer(index: int, direction: str, nbytes: int, dt_sec: float):
    if 0:
        print(f"### direction: {direction}, nbytes: {nbytes}, dt_sec: {dt_sec}")
    
    """direction: 'd2h' or 'h2d'"""
    if dt_sec <= 0 or nbytes <= 0:
        return
    ts = time.time()
    gbps = (nbytes / dt_sec) / 1e9

    with _lock:
        _buf.append((index, direction, nbytes, dt_sec, gbps))
        if len(_buf) >= BUF_MAX:
            _flush_locked()

def _flush_locked():
    newfile = not os.path.exists(TRAFFIC_LOG)
    with open(TRAFFIC_LOG, "a", buffering=1) as f:
        if newfile:
            f.write("ts,direction,bytes,dt_sec,gbps\n")
        while _buf:
            ts, d, b, dt, g = _buf.popleft()
            f.write(f"{ts:.6f},{d},{b},{dt:.9f},{g:.3f}\n")
            if 0:
                print(f"{ts:.6f},{d},{b},{dt:.9f},{g:.3f} | TRAFFIC_LOG:{TRAFFIC_LOG} \n")

def flush_transfers():
    with _lock:
        if _buf:
            _flush_locked()
################################################## CHANGE STRIP ######################################################################

def get_hash_str(token_ids: List[int], prior_hash: str = None) -> str:
    hasher = hashlib.sha256()

    if prior_hash:
        hasher.update(bytes.fromhex(prior_hash))

    for t in token_ids:
        if isinstance(t, tuple):
            # EAGLE bigram mode: hash both elements to uniquely identify the bigram
            for elem in t:
                hasher.update(elem.to_bytes(4, byteorder="little", signed=False))
        else:
            # Regular mode: single integer token
            hasher.update(t.to_bytes(4, byteorder="little", signed=False))

    return hasher.hexdigest()


def hash_str_to_int64(hash_str: str) -> int:
    """Convert SHA256 hex string to signed 64-bit integer for events.

    Takes first 16 hex characters (64 bits) and converts to signed int64 range.
    """
    # Take first 16 hex chars to get 64-bit value
    uint64_val = int(hash_str[:16], 16)
    # Convert to signed int64 range [-2^63, 2^63-1]
    if uint64_val >= 2**63:
        return uint64_val - 2**64
    return uint64_val


@dataclass
class HiCacheStorageConfig:
    tp_rank: int
    tp_size: int
    pp_rank: int
    pp_size: int
    is_mla_model: bool
    is_page_first_layout: bool
    model_name: Optional[str]
    extra_config: Optional[dict] = None


@dataclass
class HiCacheStorageExtraInfo:
    prefix_keys: Optional[List[str]] = (None,)
    extra_info: Optional[dict] = None


class HiCacheStorage(ABC):
    """
    HiCacheStorage is a class that provides a generic key-value interface for storing and retrieving KV cache.
    It abstracts the underlying storage mechanism, allowing different implementations to be used.
    """

    # todo, the page size of storage backend does not have to be the same as the same as host memory pool

    def register_mem_pool_host(self, mem_pool_host: HostKVCache):
        self.mem_pool_host = mem_pool_host

    def batch_get_v1(
        self,
        keys: List[str],
        host_indices: torch.Tensor,
        extra_info: Optional[HiCacheStorageExtraInfo] = None,
    ) -> List[bool]:
        """
        Retrieve values for multiple keys.
        Returns a list of booleans indicating success for each key.
        """
        pass

    def batch_set_v1(
        self,
        keys: List[str],
        host_indices: torch.Tensor,
        extra_info: Optional[HiCacheStorageExtraInfo] = None,
    ) -> List[bool]:
        """
        Store multiple key-value pairs.
        Returns a list of booleans indicating success for each key.
        """
        pass

    @abstractmethod
    def get(
        self,
        key: str,
        target_location: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> torch.Tensor | None:
        """
        Retrieve the value associated with the given key.
        Returns None if the key does not exist.
        """
        pass

    # TODO: Deprecate
    @abstractmethod
    def batch_get(
        self,
        keys: List[str],
        target_locations: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> List[torch.Tensor | None] | int:
        """
        Retrieve values for multiple keys.
        Returns a list of tensors or None for each key.
        """
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: Optional[Any] = None,
        target_location: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> bool:
        """
        Store the value associated with the given key.
        Returns True if the operation was successful, False otherwise.
        """
        pass

    # TODO: Deprecate
    @abstractmethod
    def batch_set(
        self,
        keys: List[str],
        values: Optional[Any] = None,
        target_locations: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> bool:
        """
        Store multiple key-value pairs.
        Returns True if all operations were successful, False otherwise.
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if the key exists in the storage.
        Returns True if the key exists, False otherwise.
        """
        pass

    # TODO: Use a finer-grained return type (e.g., List[bool])
    def batch_exists(
        self, keys: List[str], extra_info: Optional[HiCacheStorageExtraInfo] = None
    ) -> int:
        """
        Check if the keys exist in the storage.
        return the number of consecutive existing keys from the start.
        Can be overridden by subclasses for more efficient implementation.
        """
        for i in range(len(keys)):
            if not self.exists(keys[i]):
                return i
        return len(keys)

    def clear(self) -> None:
        pass

    def get_stats(self):
        return None


class HiCacheFile(HiCacheStorage):
    
    ################################################## CHANGE STRIP ######################################################################
    def calculate_tensors_size(self, values):
        total_bytes = 0
        for tensor in values:
            # Get size of each tensor in bytes when stored as uint8
            # This matches how you're saving them
            tensor_bytes = tensor.contiguous().view(dtype=torch.uint8).numel()
            total_bytes += tensor_bytes
            
        return total_bytes
    ################################################## CHANGE STRIP ######################################################################

    def __init__(
        self, storage_config: HiCacheStorageConfig, file_path: str = "/tmp/hicache"
    ):
        self.file_path = os.getenv("SGLANG_HICACHE_FILE_BACKEND_STORAGE_DIR", file_path)

        tp_rank, tp_size, model_name, is_mla_model = (
            storage_config.tp_rank,
            storage_config.tp_size,
            storage_config.model_name,
            storage_config.is_mla_model,
        )
        model_name = "-".join(model_name.split("/")) if model_name else ""
        if is_mla_model:
            self.config_suffix = f"_{model_name}"
        else:
            self.config_suffix = f"_{model_name}_{tp_rank}_{tp_size}"

        if not os.path.exists(self.file_path) and tp_rank == 0:
            os.makedirs(self.file_path)
            logger.info(f"Created HiCacheFile storage directory at {self.file_path}")

    def _get_suffixed_key(self, key: str) -> str:
        return key + self.config_suffix

    def get(
        self,
        key: str,
        target_location: torch.Tensor,
        target_sizes: Optional[Any] = None,
    ) -> torch.Tensor | None:
        key = self._get_suffixed_key(key)
        tensor_path = os.path.join(self.file_path, f"{key}.bin")
        try:
            expected = target_location.numel() * target_location.element_size()
            with open(tensor_path, "rb", buffering=0) as f:
                buf = memoryview(target_location.view(torch.uint8).contiguous().numpy())
                if f.readinto(buf) != expected:
                    raise IOError(f"Short read for {key}")
            return target_location
        except FileNotFoundError:
            logger.warning(f"Failed to fetch {key} from HiCacheFile storage.")
            return None

    ################################################## CHANGE STRIP ######################################################################
    def batch_get(
        self,
        token_ids, # NEWCHANGE. NEWTRAIL.
        keys: List[str],
        target_locations: List[torch.Tensor],
        target_sizes: Optional[Any] = None,
    ) -> List[torch.Tensor | None]:
        total_bytes = 1024 #self.calculate_tensors_size(keys)  # FIXME.REMOVEME.
        if 1:
            tprint(f"batch_get: Retrieving tensors of total size: {total_bytes} bytes")
            
        global storage_host_transfer_counter
        global total_sleep_time_s2h_ms
        enable_print_bw=0
        if storage_host_transfer_counter%SKIP_PRINT_FREQ==0:
            enable_print_bw=1
            
        if hicache_storage__debug__nodetokenids_s2h==1 and enable_print_bw==1:
            tprint("\n----------------") # 
        
        bytes_transferred = total_bytes 
        kbytes_transferred = bytes_transferred / (1024)
        mbytes_transferred = bytes_transferred / (1024 * 1024)
        global total_data_transferred_s2h
        total_data_transferred_s2h += (bytes_transferred / (1024 * 1024 * 1024)) 
        
        target_time=0
        if hicache_storage__debug__enforecethrottling==1:
            max_bw__stprefetch=100
            target_time = bytes_transferred / (max_bw__stprefetch * 1e6)

        import time # MYFUNCTION
        t0 = time.perf_counter()
        
        if 0 and hicache_storage__debug__indices==1 and enable_print_bw==1: #1 and (hicache_storage__debug__enforecethrottling==0):
            tprint(f"[CHECK_POINT: STORAGE ------> HOST] | PREFETCH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get [first eight keys: {keys[:8]}{'...' if len(keys) > 8 else ''}...] ")          
        
        result = [
            self.get(key, target_location)
            for key, target_location in zip(
                keys, target_locations or [None] * len(keys)
            )
        ]
        
        wall_ms = (time.perf_counter() - t0) * 1000
        cuda_ms = wall_ms
        target_time_ms = target_time * 1000
        transfer_rate__mbytes_per_sec = (bytes_transferred / (1024 * 1024)) / (cuda_ms / 1024)

        if hicache_storage__debug__indices==1 and enable_print_bw==1: # CHECK_POINT***
            tprint(f"[CHECK_POINT: STORAGE ------> HOST] | hiradix_storage.py/batch_get | host_indices: {host_indices[:8]} | len(host_indices) ")
            
        if hicache_storage__debug__nodetokenids_s2h==1 and enable_print_bw==1:
            print(f"[CHECK_POINT: STORAGE ------> HOST] | PREFETCH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get | node token_ids: [{','.join(map(str, token_ids))}]")
        if hicache_storage__debug__nodetext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            node_token_ids = token_ids 
            node_text = tokenizer.decode(node_token_ids)
            node_text = node_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT: STORAGE ------> HOST] | WRITE THROUGH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get | node text: {node_text}")

        # Enforce additional delay if copy was faster than target
        if hicache_storage__debug__enforecethrottling==1:
            if hicache_storage__debug__bandwidth_s2h==1 and enable_print_bw==1:
                # tprint(f"[CHECK_POINT: STORAGE ------> HOST] | PREFETCH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get | [first eight keys: {keys[:8]}{'...' if len(keys) > 8 else ''}...] ")  
                tprint(f"[CHECK_POINT: STORAGE ------> HOST] | PREFETCH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get/throttle-enforced | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms, [target_time_ms]: {target_time_ms:.3f} ms, [target BW]: {max_bw__stprefetch} MB/s | mbytes_transferred: {mbytes_transferred} MB | s2h transfer rate: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred s2h] {total_data_transferred_s2h:.2f} GB ")                        
                tprint(f"[CHECK_POINT: STORAGE ------> HOST] general statistics so far: host_storage_transfer_counter={host_storage_transfer_counter}, storage_host_transfer_counter={storage_host_transfer_counter} ")
            if wall_ms < target_time_ms:
                sleep_time_ms = target_time_ms - wall_ms
                total_sleep_time_s2h_ms += sleep_time_ms
                
                theoretical_time_ms=0
                if mbytes_transferred < LINK_CHANNEL_THRESHOLD_MB___PREFETCH: # FIXME.
                    if hicache_storage__debug__bandwidth_s2h==1 and enable_print_bw==1:
                        tprint(f"[CHECK_POINT: STORAGE ------> HOST] sleeping for {sleep_time_ms:.3f} ms ... (sleep_time_ms: {sleep_time_ms:.3f} ms) ")
                    time.sleep(((target_time_ms - wall_ms) / 1000))
                    theoretical_time_ms = target_time_ms
                else:
                    theoretical_time_ms = wall_ms
                
                record_transfer(storage_host_transfer_counter, "s2h", bytes_transferred, (theoretical_time_ms / 1024))   # storage -> host
            else:
                record_transfer(storage_host_transfer_counter, "s2h", bytes_transferred, (wall_ms / 1024))   # storage -> host
        else:
            if hicache_storage__debug__bandwidth_s2h==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT: STORAGE ------> HOST] | PREFETCH | #{storage_host_transfer_counter} | hiradix_storage.py/batch_get | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms | kbytes_transferred: {kbytes_transferred} KB | s2h transfer rate: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred s2h] {total_data_transferred_s2h:.3f} GB ")                     
                tprint(f"[CHECK_POINT] | general statistics so far: host_storage_transfer_counter={host_storage_transfer_counter}, storage_host_transfer_counter={storage_host_transfer_counter} ")
                
        storage_host_transfer_counter += 1

        return result
    ################################################## CHANGE STRIP ######################################################################

    def set(
        self,
        key: str,
        value: Optional[Any] = None,
        target_location: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> bool:
        if self.exists(key):
            logger.debug(f"Key {key} already exists. Skipped.")
            return True

        key = self._get_suffixed_key(key)
        tensor_path = os.path.join(self.file_path, f"{key}.bin")
        try:
            value.contiguous().view(dtype=torch.uint8).numpy().tofile(tensor_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save tensor {key}: {e}")
            return False

    ################################################## CHANGE STRIP ######################################################################
    def batch_set(
        self,
        token_ids, # NEWCHANGE. NEWTRAIL.
        keys: List[str],
        values: Optional[Any] = None,
        target_locations: Optional[Any] = None,
        target_sizes: Optional[Any] = None,
    ) -> bool:
        
        total_bytes = self.calculate_tensors_size(values)
        if 0:
            logger.info(f"Storing tensors of total size: {total_bytes} bytes")
       
        global host_storage_transfer_counter
        global total_sleep_time_h2s_ms
        enable_print_bw=0
        if host_storage_transfer_counter%SKIP_PRINT_FREQ==0:
            enable_print_bw=1
            
        if hicache_storage__debug__nodetokenids_h2s==1 and enable_print_bw==1:
            tprint("\n----------------") # 
        
        bytes_transferred = total_bytes 
        kbytes_transferred = bytes_transferred / (1024)
        mbytes_transferred = bytes_transferred / (1024 * 1024)
        global total_data_transferred_h2s
        total_data_transferred_h2s += (bytes_transferred / (1024 * 1024 * 1024)) 
        
        target_time=0
        if hicache_storage__debug__enforecethrottling==1:
            max_bw__stwritethrough=100
            target_time = bytes_transferred / (max_bw__stwritethrough * 1e6)
        
        import time # MYFUNCTION
        t0 = time.perf_counter()

        if hicache_storage__debug__nodetokenids_h2s==1 and enable_print_bw==1: #host_storage_transfer_counter%SKIP_PRINT_FREQ==10:
            tprint(f"[CHECK_POINT] hiradix_cache.py/writing_check -> hiradix_cache.py/write_backup_storage ->  cache_controller.py/write_storage [QUEUE] -> [QUEUE] cache_controller.py/backup_thread_func -> hicache_storage.py/batch_set  ")
        if 0 and hicache_storage__debug__indices==1 and enable_print_bw==1: #1 and (hicache_storage__debug__enforecethrottling==0):
            tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set [first eight keys: {keys[:8]}{'...' if len(keys) > 8 else ''}...] ")          
       
        for key, value in zip(keys, values): 
            if not self.set(key, value):
                return False
                
        wall_ms = (time.perf_counter() - t0) * 1000
        cuda_ms = wall_ms
        target_time_ms = target_time * 1000
        transfer_rate__mbytes_per_sec = (bytes_transferred / (1024 * 1024)) / (cuda_ms / 1024)
        
        if hicache_storage__debug__indices==1 and enable_print_bw==1: # CHECK_POINT***
            tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set | host_indices: {host_indices[:8]} | len(host_indices) ")
            
        if hicache_storage__debug__nodetokenids_h2s==1 and enable_print_bw==1:
            tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set | node token_ids: [{','.join(map(str, token_ids))}]")
            # tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set...") 
        if hicache_storage__debug__nodetext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            node_token_ids = token_ids 
            node_text = tokenizer.decode(node_token_ids)
            node_text = node_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set | node text: {node_text}")
        
        # Enforce additional delay if copy was faster than target
        if hicache_storage__debug__enforecethrottling==1:
            if hicache_storage__debug__bandwidth_h2s==1 and enable_print_bw==1:  
                tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set/throttle-enforced | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms, [target_time_ms]: {target_time_ms:.3f} ms, [target BW]: {max_bw__stwritethrough} MB/s | mbytes_transferred: {mbytes_transferred} MB | h2s transfer rate: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred h2s] {total_data_transferred_h2s:.2f} GB ")                        
                tprint(f"[CHECK_POINT: HOST ------> STORAGE] general statistics so far: host_storage_transfer_counter={host_storage_transfer_counter}, storage_host_transfer_counter={storage_host_transfer_counter} ")
            if wall_ms < target_time_ms:
                sleep_time_ms = target_time_ms - wall_ms
                total_sleep_time_h2s_ms += sleep_time_ms
                
                theoretical_time_ms=0
                if mbytes_transferred < LINK_CHANNEL_THRESHOLD_MB___WRITETHROUGH: # FIXME.
                    if hicache_storage__debug__bandwidth_h2s==1 and enable_print_bw==1:
                        tprint(f"[CHECK_POINT: HOST ------> STORAGE] sleeping for {sleep_time_ms:.3f} ms ... (sleep_time_ms: {sleep_time_ms:.3f} ms) ")
                    time.sleep(((target_time_ms - wall_ms) / 1000))
                    theoretical_time_ms = target_time_ms
                else:
                    theoretical_time_ms = wall_ms
                
                record_transfer(host_storage_transfer_counter, "h2s", bytes_transferred, (theoretical_time_ms / 1024))   # host -> storage
            else:
                record_transfer(host_storage_transfer_counter, "h2s", bytes_transferred, (wall_ms / 1024))   # host -> storage # len(keys): {len(keys)}
        else:
            if hicache_storage__debug__bandwidth_h2s==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT: HOST ------> STORAGE] | #{host_storage_transfer_counter} | hiradix_storage.py/batch_set | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms | kbytes_transferred: {kbytes_transferred} KB | h2s transfer rate: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred h2s] {total_data_transferred_h2s:.3f} GB ")                     
                tprint(f"[CHECK_POINT] | general statistics so far: host_storage_transfer_counter={host_storage_transfer_counter}, storage_host_transfer_counter={storage_host_transfer_counter} ")
                
        host_storage_transfer_counter += 1
        return True
    ################################################## CHANGE STRIP ######################################################################

    def exists(self, key: str) -> bool:
        key = self._get_suffixed_key(key)
        tensor_path = os.path.join(self.file_path, f"{key}.bin")
        return os.path.exists(tensor_path)

    def clear(self) -> bool:
        try:
            for filename in os.listdir(self.file_path):
                file_path = os.path.join(self.file_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("Cleared all entries in HiCacheFile storage.")
            return True
        except Exception as e:
            logger.error(f"Failed to clear HiCacheFile storage: {e}")
            return False
