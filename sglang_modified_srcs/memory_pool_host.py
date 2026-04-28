import abc
import logging
import threading
from collections import defaultdict
from functools import wraps
from typing import Optional

from sglang.jit_kernel.hicache import can_use_hicache_jit_kernel
from sglang.jit_kernel.hicache import (
    transfer_hicache_all_layer as jit_transfer_hicache_all_layer,
)
from sglang.jit_kernel.hicache import (
    transfer_hicache_one_layer as jit_transfer_hicache_one_layer,
)
from sglang.srt.mem_cache.memory_pool import KVCache, MHATokenToKVPool, MLATokenToKVPool
from sglang.srt.utils import is_cuda, is_npu, is_xpu

_is_cuda = is_cuda()
_is_npu = is_npu()
_is_xpu = is_xpu()
if not (_is_npu or _is_xpu):
    from sgl_kernel.kvcacheio import (
        transfer_kv_all_layer,
        transfer_kv_all_layer_direct_lf_pf,
        transfer_kv_all_layer_lf_pf,
        transfer_kv_all_layer_lf_ph,
        transfer_kv_all_layer_mla,
        transfer_kv_all_layer_mla_lf_pf,
        transfer_kv_direct,
        transfer_kv_per_layer,
        transfer_kv_per_layer_direct_pf_lf,
        transfer_kv_per_layer_mla,
        transfer_kv_per_layer_mla_pf_lf,
        transfer_kv_per_layer_pf_lf,
        transfer_kv_per_layer_ph_lf,
    )
if _is_npu:
    from sgl_kernel_npu.kvcacheio import TransferDirection, transfer_kv_dim_exchange

logger = logging.getLogger(__name__)

################################################## CHANGE STRIP ######################################################################
import psutil
import torch
import os
import sys # NEWCHANGE
import subprocess

mem_pool_host__debug__bandwidth=0 
mem_pool_host__debug__nodetokenids=0 

mem_pool_host__debug=0
mem_pool_host__debug__indices=0 
mem_pool_host__debug__enforecethrottling=0 
mem_pool_host__debug__prefixtokenids=0
mem_pool_host__debug__prefixtext=0 
mem_pool_host__debug__nodetext=0 

SKIP_PRINT_FREQ=10000 # 100
# memory bandwidths
LINK_CHANNEL_THRESHOLD_MB___WRITEBACK=20
LINK_CHANNEL_THRESHOLD_MB___LOADBACK=20

from datetime import datetime
def tprint(*args, **kwargs):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")  # Include milliseconds
    print(f"[{ts}]", *args, **kwargs)
    sys.stdout.flush() 
   
host_device_transfer_counter=0
device_host_transfer_counter=0
total_sleep_time_d2h_ms=0
total_sleep_time_h2d_ms=0
total_data_transferred_d2h=0
total_data_transferred_h2d=0
################################################## CHANGE STRIP ######################################################################

################################################## CHANGE STRIP ######################################################################
import json
def print_cpu_stat(): # NEWCHANGE.
    try:
        # Run the cpustat command with '-cp' to get stats
        result = subprocess.check_output(['free', '-g'], stderr=subprocess.STDOUT)
        # Decode the result from bytes to a string and print it
        print(result.decode('utf-8'))
    except FileNotFoundError:
        print("Error: 'cpustat' is not installed on this system.")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing 'cpustat': {e.output.decode('utf-8')}")
    except Exception as e:
        print(f"Unexpected error: {e}") 

# pip3 install gpustat
def print_gpu_stat():
    return
    try:
        # Run the gpustat command with '-cp' to get stats
        result = subprocess.check_output(['gpustat', '-cp'], stderr=subprocess.STDOUT)
        # Decode the result from bytes to a string and print it
        print(result.decode('utf-8'))
    except FileNotFoundError:
        print("Error: 'gpustat' is not installed on this system.")
    except subprocess.CalledProcessError as e:
        print(f"Error while executing 'gpustat': {e.output.decode('utf-8')}")
    except Exception as e:
        print(f"Unexpected error: {e}")   
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

def synchronized(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)

    return wrapper


class HostTensorAllocator(abc.ABC):
    def __init__(self):
        """Initialize the HostTensorAllocator."""
        self.dtype = None
        self.dims = None

    def allocate(self, dims: tuple, dtype: torch.dtype, device: str) -> torch.Tensor:
        """Allocate a tensor of given dims and dtype on the memory."""
        self.dtype = dtype
        self.dims = dims
        tensor = torch.empty(dims, dtype=dtype, device=device)
        return tensor


def get_allocator_from_storage(allocator_type):
    if allocator_type == "mooncake":
        try:
            from sglang.srt.mem_cache.storage.mooncake_store.mooncake_store import (
                MooncakeHostTensorAllocator,
            )

            return MooncakeHostTensorAllocator()
        except ImportError:
            logger.warning(
                "Mooncake's tensor allocator requires mooncake >= 0.3.8.post1. "
                "Please upgrade Mooncake by 'pip install mooncake-transfer-engine --upgrade'. "
                "Fallback to use default allocator."
            )
            return HostTensorAllocator()
    else:
        return HostTensorAllocator()


def alloc_with_host_register(
    dims,
    dtype: torch.dtype,
    device: str,
    pin_memory: bool,
    allocator: HostTensorAllocator,
) -> torch.Tensor:
    """
    Allocate tensor and register host memory with cudaHostRegister.
    CudaHostRegister only applies when pin_memory=True.
    """
    buffer = allocator.allocate(dims, dtype=dtype, device=device)
    if pin_memory:
        torch.cuda.cudart().cudaHostRegister(
            buffer.data_ptr(), buffer.numel() * buffer.element_size(), 0
        )
    return buffer


def alloc_with_pin_memory(
    dims,
    dtype: torch.dtype,
    device: str,
    pin_memory: bool,
    allocator: None,
) -> torch.Tensor:
    """
    Allocate tensor using PyTorch's built-in pin_memory flag.
    """
    buffer = torch.empty(dims, dtype=dtype, device=device, pin_memory=pin_memory)
    return buffer


ALLOC_MEMORY_FUNCS = defaultdict(
    lambda: alloc_with_host_register,
    {
        "npu": alloc_with_pin_memory,
    },
)


class HostKVCache(abc.ABC):

    def __init__(
        self,
        device_pool: KVCache,
        host_to_device_ratio: float,
        host_size: int,
        page_size: int,
        layout: str,
        pin_memory: bool,
        device: str,
        allocator_type: str = "default",
    ):
        self.device_pool = device_pool
        self.page_size = page_size
        self.layout = layout
        self.pin_memory = pin_memory
        self.device = device
        self.allocator = get_allocator_from_storage(allocator_type)

        self.dtype = device_pool.store_dtype
        self.size_per_token = self.get_size_per_token()
        if host_size > 0:
            self.size = int(host_size * 1e9 // self.size_per_token)
        else:
            self.size = int(device_pool.size * host_to_device_ratio)
        # Align up the host memory pool size to the page size
        self.page_num = self.size // self.page_size + 1
        self.size = self.page_num * self.page_size
        self.start_layer = device_pool.start_layer
        self.end_layer = device_pool.end_layer

        assert (
            self.size > device_pool.size
        ), "The host memory should be larger than the device memory with the current protocol"

        # Verify there is enough available host memory.
        host_mem = psutil.virtual_memory()
        requested_bytes = self.size * self.size_per_token
        # preserve at least 10GB for other usage
        ten_gb = 10 * (1024**3)
        available_bytes = host_mem.available - ten_gb
        if requested_bytes > available_bytes:
            raise ValueError(
                f"Not enough host memory available. Requesting "
                f"{requested_bytes / 1e9:.2f} GB but only have "
                f"{available_bytes / 1e9:.2f} GB free. Please reduce the "
                f"size of the hierarchical cache."
            )
        else:
            logger.info(
                f"Allocating {requested_bytes / 1e9:.2f} GB host memory for hierarchical KV cache."
            )

        self.kv_buffer = self.init_kv_buffer()

        # A lock for synchronized operations on memory allocation and state transitions.
        self.lock = threading.RLock()
        self.clear()

    @abc.abstractmethod
    def get_size_per_token(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def init_kv_buffer(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def load_to_device_per_layer(
        self, device_pool, host_indices, device_indices, layer_id, io_backend
    ) -> None:
        """
        Load KV data from the host memory pool to the device memory pool for a specific layer.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def backup_from_device_all_layer(
        self, device_pool, host_indices, device_indices, io_backend
    ) -> None:
        """
        Backup KV data from the device memory pool to the host memory pool for all layers.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_data_page(self, index, flat: bool = True) -> torch.Tensor:
        """
        Get a flat data page from the host memory pool.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_dummy_flat_data_page(self) -> torch.Tensor:
        """
        Get a dummy flat data page from the host memory pool.
        This is used for prefetching or initializing empty pages.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_from_flat_data_page(self, index: int, data_page: torch.Tensor) -> None:
        """
        Set a flat data page to the host memory pool.
        """
        raise NotImplementedError()

    @synchronized
    def clear(self):
        # Initialize memory states and tracking structures.
        self.mem_state = torch.zeros(
            (self.size,), dtype=torch.uint8, device=self.device
        )
        self.free_slots = torch.arange(self.size, dtype=torch.int64)

    def available_size(self):
        return len(self.free_slots)

    @synchronized
    def alloc(self, need_size: int) -> Optional[torch.Tensor]:
        assert (
            need_size % self.page_size == 0
        ), "The requested size should be a multiple of the page size."
        if need_size > self.available_size():
            return None

        select_index = self.free_slots[:need_size]
        self.free_slots = self.free_slots[need_size:]

        return select_index

    @synchronized
    def free(self, indices: torch.Tensor) -> int:
        self.free_slots = torch.cat([self.free_slots, indices])
        return len(indices)


class MHATokenToKVPoolHost(HostKVCache):
    device_pool: MHATokenToKVPool

    def __init__(
        self,
        device_pool: MHATokenToKVPool,
        host_to_device_ratio: float,
        host_size: int,
        page_size: int,
        layout: str,
        pin_memory: bool = True,
        device: str = "cpu",
        allocator_type: str = "default",
    ):
        super().__init__(
            device_pool,
            host_to_device_ratio,
            host_size,
            page_size,
            layout,
            pin_memory,
            device,
            allocator_type,
        )
        self.element_dim = self.device_pool.head_num * self.device_pool.head_dim
        self.can_use_jit = _is_cuda and can_use_hicache_jit_kernel(
            element_size=self.element_dim * self.dtype.itemsize
        )

        self.k_data_refs = [self.k_buffer[i] for i in range(self.layer_num)]
        self.v_data_refs = [self.v_buffer[i] for i in range(self.layer_num)]
        self.k_data_ptrs = torch.tensor(
            [x.data_ptr() for x in self.k_data_refs],
            dtype=torch.uint64,
            device=self.device_pool.device,
        )
        self.v_data_ptrs = torch.tensor(
            [x.data_ptr() for x in self.v_data_refs],
            dtype=torch.uint64,
            device=self.device_pool.device,
        )

    def get_size_per_token(self):
        self.head_num = self.device_pool.head_num
        self.head_dim = self.device_pool.head_dim
        self.layer_num = self.device_pool.layer_num

        return self.head_dim * self.head_num * self.layer_num * self.dtype.itemsize * 2

    def get_ksize_per_token(self):
        return self.get_size_per_token() // 2

    def init_kv_buffer(self):
        if self.layout == "layer_first":
            dims = (2, self.layer_num, self.size, self.head_num, self.head_dim)
        elif self.layout == "page_first":
            dims = (2, self.size, self.layer_num, self.head_num, self.head_dim)
        elif self.layout == "page_first_direct":
            dims = (
                2,
                self.page_num,
                self.layer_num,
                self.page_size,
                self.head_num,
                self.head_dim,
            )
        elif self.layout == "page_head":
            dims = (
                2,
                self.page_num,
                self.head_num,
                self.page_size,
                self.layer_num,
                self.head_dim,
            )
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        self.token_stride_size = self.head_num * self.head_dim * self.dtype.itemsize
        self.layout_dim = self.token_stride_size * self.layer_num

        alloc_func = ALLOC_MEMORY_FUNCS[self.device_pool.device]
        buffer = alloc_func(
            dims,
            dtype=self.dtype,
            device=self.device,
            pin_memory=self.pin_memory,
            allocator=self.allocator,
        )
        return buffer

    @property
    def k_buffer(self):
        return self.kv_buffer[0]

    @property
    def v_buffer(self):
        return self.kv_buffer[1]

    ################################################## CHANGE STRIP ######################################################################
    def load_to_device_per_layer(
        self,
        # token_ids, # NEWCHANGE. NEWTRAIL.
        device_pool,
        host_indices,
        device_indices,
        layer_id,
        io_backend,
    ):
        """
        Load KV data from the host memory pool to the device memory pool for a specific layer.
        """
        
        token_ids=[] # node.key.token_ids 
        
        global host_device_transfer_counter
        global total_sleep_time_h2d_ms
        enable_print_bw=0
        if host_device_transfer_counter%SKIP_PRINT_FREQ==0:
            enable_print_bw=1
            
        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1:
            tprint("\n----------------") # 
            
        if mem_pool_host__debug==1 and enable_print_bw==1: # /usr/local/lib/python3.12/dist-packages/sgl_kernel/kvcacheio.py 
            tprint(f"[CHECK_POINT: HOST ------> DEVICE] | LOADBACK | | memory_pool_host.py/load_to_device_per_layer -> [torch.ops.sgl_kernel.transfer_kv_per_layer][/usr/local/lib/python3.12/dist-packages/sgl_kernel/kvcacheio.py] | [host_indices: {host_indices} (len(host_indices): {len(host_indices)}) | device_indices: {device_indices}] ")
        if mem_pool_host__debug==1 and enable_print_bw==1: #1 and (mem_pool_host__debug__enforecethrottling==0):
            tprint(f"[CHECK_POINT: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer -> torch.ops.sgl_kernel.transfer_kv_per_layer [first eight host_indices: {host_indices[:8]}{'...' if len(host_indices) > 8 else ''}...] ") 
            
        num_items = 1
        for dim in host_indices.shape:
            num_items *= dim

        # BENCH: llama-7b takes in 16KB per token per layer 
        num_bytes_per_token_per_layer = self.head_num * self.head_dim * self.dtype.itemsize * 2
        num_bytes_per_token_all_layers = 1 * num_bytes_per_token_per_layer
        num_tokens_per_block = self.page_size # 16
        num_bytes_per_block = num_tokens_per_block * num_bytes_per_token_all_layers
        bytes_transferred = num_items * num_bytes_per_block
        kbytes_transferred = bytes_transferred / (1024)
        mbytes_transferred = bytes_transferred / (1024 * 1024)
        global total_data_transferred_h2d
        total_data_transferred_h2d += (bytes_transferred / (1024 * 1024 * 1024))

        target_time=0
        if mem_pool_host__debug__enforecethrottling==1:
            max_bw__loadback=100
            target_time = bytes_transferred / (max_bw__loadback * 1e6)
        
        import time # MYFUNCTION
        t0 = time.perf_counter()
        # GPU event timing
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        
        if 0:
            tprint(f"^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ memory_pool_host.py / load_to_device_per_layer / io_backend: {io_backend}, self.layout: {self.layout}.")

        if io_backend == "kernel":
            if self.layout == "layer_first":
                transfer_kv_per_layer( # this is the kernel used as default.
                    src_k=self.k_buffer[layer_id],
                    dst_k=device_pool.k_buffer[layer_id], # CHECK_POINT
                    src_v=self.v_buffer[layer_id],
                    dst_v=device_pool.v_buffer[layer_id],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    item_size=self.token_stride_size,
                )
            elif self.layout == "page_first":
                transfer_kv_per_layer_pf_lf(
                    src_k=self.k_buffer,
                    dst_k=device_pool.k_buffer[layer_id],
                    src_v=self.v_buffer,
                    dst_v=device_pool.v_buffer[layer_id],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    layer_id=layer_id,
                    item_size=self.token_stride_size,
                    src_layout_dim=self.layout_dim,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "direct":
            if self.layout == "layer_first":
                transfer_kv_direct(
                    src_layers=[self.k_buffer[layer_id], self.v_buffer[layer_id]],
                    dst_layers=[
                        device_pool.k_buffer[layer_id],
                        device_pool.v_buffer[layer_id],
                    ],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    page_size=self.page_size,
                )
            elif self.layout == "page_first_direct":
                transfer_kv_per_layer_direct_pf_lf(
                    src_ptrs=[self.k_buffer, self.v_buffer],
                    dst_ptrs=[
                        device_pool.k_buffer[layer_id],
                        device_pool.v_buffer[layer_id],
                    ],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    layer_id=layer_id,
                    page_size=self.page_size,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        else:
            raise ValueError(f"Unsupported IO backend: {io_backend}")

        end.record()
        torch.cuda.synchronize()
        cuda_ms = start.elapsed_time(end)
        wall_ms = (time.perf_counter() - t0) * 1000
        target_time_ms = target_time * 1000
        transfer_rate__mbytes_per_sec = (bytes_transferred / (1024 * 1024)) / (cuda_ms / 1024)        

        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1: #if host_device_transfer_counter%SKIP_PRINT_FREQ==100:
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}] hiradix_cache.py/init_load_back -> hiradix_cache.py/load_back ->  cache_controller.py/load [QUEUE] -> [QUEUE] cache_controller.py/start_loading -> mem_pool_host.py/load_to_device_per_layer  ")
        if 0 and mem_pool_host__debug==1 and enable_print_bw==1:
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | hiradix_cache.py/init_load_back -> memory_pool_host.py/load_to_device_per_layer | node.key {last_node.key}, node.value {last_node.value}, tokens for node {last_node.id} ")

        if 0 and 0 and mem_pool_host__debug__prefixtokenids==1 and enable_print_bw==1:
            prefix_token_ids = self.get_prefix_tokens(node)
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | memory_pool_host.py/load_to_device_per_layer -> hiradix_cache.py/load_back")# | prefix token_ids: [{','.join(map(str, prefix_token_ids))}]")
        if 0 and mem_pool_host__debug__prefixtext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            prefix_token_ids = self.get_prefix_tokens(node)
            prefix_text = tokenizer.decode(prefix_token_ids)
            prefix_text = prefix_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | memory_pool_host.py/load_to_device_per_layer -> hiradix_cache.py/load_back | prefix text: {prefix_text}")
            
        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1:
            node_token_ids = token_ids
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | memory_pool_host.py/load_to_device_per_layer -> hiradix_cache.py/load_back")# | node token_ids: {[{','.join(map(str, node_token_ids))}]}")
        if mem_pool_host__debug__nodetext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            node_token_ids = token_ids
            node_text = tokenizer.decode(node_token_ids)
            node_text = node_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | memory_pool_host.py/load_to_device_per_layer -> hiradix_cache.py/load_back | node text: {node_text}")

        # Enforce additional delay if copy was faster than target
        if mem_pool_host__debug__enforecethrottling==1:
            if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer | [first eight (of {len(host_indices)}) host_indices: {host_indices[:8].tolist()}{'...' if len(host_indices) > 8 else ''}...] ") 
                tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer/throttle-enforced | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms, [target_time_ms]: {target_time_ms:.3f} ms, [target BW]: {max_bw__loadback} MB/s | [mbytes_transferred]: {mbytes_transferred} MB | [h2d transfer rate]: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred h2d] {total_data_transferred_h2d:.2f} GB | num_items: {num_items} ")
            if wall_ms < target_time_ms:
                sleep_time_ms = target_time_ms - wall_ms
                total_sleep_time_h2d_ms += sleep_time_ms

                theoretical_time_ms=0
                if mbytes_transferred < LINK_CHANNEL_THRESHOLD_MB___LOADBACK: # FIXME.
                    if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                        tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] sleeping for {sleep_time_ms:.3f} ms ... (sleep_time_ms: {sleep_time_ms:.3f} ms) ")
                    time.sleep(((target_time_ms - wall_ms) / 1000))
                    theoretical_time_ms = target_time_ms
                else:
                    theoretical_time_ms = wall_ms
           
                record_transfer(host_device_transfer_counter, "h2d", bytes_transferred, (theoretical_time_ms / 1024))   # host -> device
            else:
                record_transfer(host_device_transfer_counter, "h2d", bytes_transferred, (wall_ms / 1024))   # host -> device
        else:
            if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms | kbytes_transferred: {kbytes_transferred} KB | [Total bytes transferred h2d] {total_data_transferred_h2d:.3f} GB | [h2d transfer rate]: {transfer_rate__mbytes_per_sec:.1f} MB/s | num_items: {num_items} ")                     
            if 0:#mem_pool_host__debug__bandwidth==1:
                tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer | self.head_num: {self.head_num} | self.head_dim: {self.head_dim} | self.dtype.itemsize: {self.dtype.itemsize} | self.layer_num: 1 | num_items: {num_items}")
                tprint(f"[CHECK_POINT #{host_device_transfer_counter}: HOST ------> DEVICE] | LOADBACK | memory_pool_host.py/load_to_device_per_layer | num_bytes_per_token_per_layer: {num_bytes_per_token_per_layer} bytes | num_bytes_per_token_all_layers: {num_bytes_per_token_all_layers} bytes | num_tokens_per_block: {num_tokens_per_block} | num_bytes_per_block: {num_bytes_per_block} bytes | bytes_transferred: {bytes_transferred} bytes")
        host_device_transfer_counter += 1
    ################################################## CHANGE STRIP ######################################################################
    
    ################################################## CHANGE STRIP ######################################################################
    def backup_from_device_all_layer(
        self, 
        # token_ids,
        # node, # NEWCHANGE. NEWTRAIL.
        # evict_host_counter, # NEWCHANGE. NEWTRAIL.
        device_pool, host_indices, device_indices, io_backend
    ):
        token_ids=[] # node.key.token_ids 
        evict_host_counter=0 # REMOVEME.
        
        """
        Backup KV data from the device memory pool to the host memory pool for all layers.
        """
        global device_host_transfer_counter
        global total_sleep_time_d2h_ms
        enable_print_bw=0
        if device_host_transfer_counter%SKIP_PRINT_FREQ==0:
            enable_print_bw=1
            
        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1:
            tprint("\n----------------") # 
        
        num_items = 1
        for dim in device_indices.shape:
            num_items *= dim
        
        # BENCH: llama-7b takes in 16KB per token per layer 
        num_bytes_per_token_per_layer = self.head_num * self.head_dim * self.dtype.itemsize * 2
        num_bytes_per_token_all_layers = self.layer_num * num_bytes_per_token_per_layer
        num_tokens_per_block = self.page_size # 16
        num_bytes_per_block = num_tokens_per_block * num_bytes_per_token_all_layers
        bytes_transferred = num_items * num_bytes_per_block
        kbytes_transferred = bytes_transferred / (1024)
        mbytes_transferred = bytes_transferred / (1024 * 1024)
        global total_data_transferred_d2h
        total_data_transferred_d2h += (bytes_transferred / (1024 * 1024 * 1024)) 
        
        target_time=0
        if mem_pool_host__debug__enforecethrottling==1:
            max_bw__writeback=100
            target_time = bytes_transferred / (max_bw__writeback * 1e6)
        
        import time # MYFUNCTION
        t0 = time.perf_counter()
        # GPU event timing
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        
        if 0:
            tprint(f"^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ memory_pool_host.py / backup_from_device_all_layer / io_backend: {io_backend}, self.layout: {self.layout}.")

        if mem_pool_host__debug==1: # /usr/local/lib/python3.12/dist-packages/sgl_kernel/kvcacheio.py  
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer -> [torch.ops.sgl_kernel.transfer_kv_all_layer][/usr/local/lib/python3.12/dist-packages/sgl_kernel/kvcacheio.py][/usr/local/lib/python3.12/dist-packages/torch/_ops.py] | device_indices: {device_indices} (len(device_indices): {len(device_indices)}) | [host_indices: {host_indices}] ")          
        if mem_pool_host__debug__indices==1: #1 and (mem_pool_host__debug__enforecethrottling==0):
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer -> torch.ops.sgl_kernel.transfer_kv_all_layer [first eight host_indices: {host_indices[:8]}{'...' if len(host_indices) > 8 else ''}...] ")          
       
        if io_backend == "kernel":
            if self.layout == "layer_first": # this is the kernel used as default.
                transfer_kv_all_layer( # torch.ops.sgl_kernel.transfer_kv_all_layer(
                    src_k_layers=device_pool.k_data_ptrs,
                    dst_k_layers=self.k_data_ptrs,
                    src_v_layers=device_pool.v_data_ptrs,
                    dst_v_layers=self.v_data_ptrs,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    item_size=self.token_stride_size,
                    num_layers=self.layer_num,
                )
            elif self.layout == "page_first":
                transfer_kv_all_layer_lf_pf(
                    src_k_layers=device_pool.k_data_ptrs,
                    dst_k=self.k_buffer,
                    src_v_layers=device_pool.v_data_ptrs,
                    dst_v=self.v_buffer,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    item_size=self.token_stride_size,
                    dst_layout_dim=self.layout_dim,
                    num_layers=self.layer_num,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "direct":
            if self.layout == "layer_first":
                transfer_kv_direct(
                    src_layers=device_pool.k_buffer + device_pool.v_buffer,
                    dst_layers=self.k_data_refs + self.v_data_refs,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    page_size=self.page_size,
                )
            elif self.layout == "page_first_direct":
                transfer_kv_all_layer_direct_lf_pf(
                    src_ptrs=device_pool.k_buffer + device_pool.v_buffer,
                    dst_ptrs=[self.k_buffer, self.v_buffer],
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    page_size=self.page_size,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        else:
            raise ValueError(f"Unsupported IO backend: {io_backend}")
            
        end.record()
        torch.cuda.synchronize()
        cuda_ms = start.elapsed_time(end)
        wall_ms = (time.perf_counter() - t0) * 1000
        target_time_ms = target_time * 1000
        transfer_rate__mbytes_per_sec = (bytes_transferred / (1024 * 1024)) / (cuda_ms / 1024)
        
        # write to host if the node is not backuped
        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1:
            tprint(f"[CHECK_POINT] hiradix_cache.py/_inc_hit_count -> hiradix_cache.py/write_backup ->  cache_controller.py/write [QUEUE] -> [QUEUE] cache_controller.py/start_writing -> mem_pool_host.py/backup_from_device_all_layer")
        if mem_pool_host__debug==1:
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | memory_pool_host.py/backup_from_device_all_layer | node.key: {node.key[:10]} | node.value: {node.value[:10]} | node.hit_count: {node.hit_count}, self.write_through_threshold: {self.write_through_threshold}")
        
        if mem_pool_host__debug__prefixtokenids==1 and enable_print_bw==1:
            prefix_token_ids = token_ids # REMOVEME # self.get_prefix_tokens(node)
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | memory_pool_host.py/backup_from_device_all_layer")# | prefix token_ids: [{','.join(map(str, prefix_token_ids))}]")
        if mem_pool_host__debug__prefixtext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            prefix_token_ids = self.get_prefix_tokens(node)
            prefix_text = tokenizer.decode(prefix_token_ids)
            prefix_text = prefix_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | memory_pool_host.py/backup_from_device_all_layer | prefix text: {prefix_text}")
            
        if mem_pool_host__debug__nodetokenids==1 and enable_print_bw==1:
            node_token_ids = token_ids 
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | memory_pool_host.py/backup_from_device_all_layer")# | node token_ids: [{','.join(map(str, node_token_ids))}]")
            tprint(f"[CHECK_POINT] | general statistics so far: device_host_transfer_counter={device_host_transfer_counter}, device_host_transfer_counter={device_host_transfer_counter}, evict_host_counter={evict_host_counter}, self.page_size={self.page_size} ")
        if mem_pool_host__debug__nodetext==1 and enable_print_bw==1:
            tokenizer = self.get_tokenizer(LLM_MODEL)
            node_token_ids = token_ids 
            node_text = tokenizer.decode(node_token_ids)
            node_text = node_text.replace('\n', ' ').replace('\r', ' ').strip() # Or if you specifically want to target newlines while keeping other whitespace:
            tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | memory_pool_host.py/backup_from_device_all_layer | node text: {node_text}")
        
        # Enforce additional delay if copy was faster than target
        if mem_pool_host__debug__enforecethrottling==1:
            if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer | [first eight (of {len(host_indices)}) host_indices: {host_indices[:8].tolist()}{'...' if len(host_indices) > 8 else ''}...] ")  
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer/throttle-enforced | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms, [target_time_ms]: {target_time_ms:.3f} ms, [target BW]: {max_bw__writeback} MB/s | [mbytes_transferred]: {mbytes_transferred} MB | [d2h transfer rate]: {transfer_rate__mbytes_per_sec:.1f} MB/s | [Total bytes transferred d2h] {total_data_transferred_d2h:.2f} GB | num_items: {num_items} ")                        
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] general statistics so far: device_host_transfer_counter={device_host_transfer_counter}, host_device_transfer_counter={host_device_transfer_counter}, self.page_size={self.page_size} ")
            if wall_ms < target_time_ms:
                sleep_time_ms = target_time_ms - wall_ms
                total_sleep_time_d2h_ms += sleep_time_ms
                
                theoretical_time_ms=0
                if mbytes_transferred < LINK_CHANNEL_THRESHOLD_MB___WRITEBACK: # FIXME.
                    if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                        tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] sleeping for {sleep_time_ms:.3f} ms ... (sleep_time_ms: {sleep_time_ms:.3f} ms) ")
                    time.sleep(((target_time_ms - wall_ms) / 1000))
                    theoretical_time_ms = target_time_ms
                else:
                    theoretical_time_ms = wall_ms
                    
                record_transfer(device_host_transfer_counter, "d2h", bytes_transferred, (theoretical_time_ms / 1024))   # device -> host
            else:
                record_transfer(device_host_transfer_counter, "d2h", bytes_transferred, (wall_ms / 1024))   # device -> host
        else:
            if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1:
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer | [WALL] {wall_ms:.3f} ms | [CUDA] {cuda_ms:.3f} ms | kbytes_transferred: {kbytes_transferred} KB | [Total bytes transferred d2h] {total_data_transferred_d2h:.3f} GB | [d2h transfer rate]: {transfer_rate__mbytes_per_sec:.1f} MB/s | num_items: {num_items} ")                     
                tprint(f"[CHECK_POINT] | general statistics so far: device_host_transfer_counter={device_host_transfer_counter}, host_device_transfer_counter={host_device_transfer_counter}, self.page_size={self.page_size} ")
            if mem_pool_host__debug__bandwidth==1 and enable_print_bw==1 and device_host_transfer_counter < 16:
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer | self.head_num: {self.head_num} | self.head_dim: {self.head_dim} | self.dtype.itemsize: {self.dtype.itemsize} | self.layer_num: {self.layer_num} | num_items: {num_items}")
                tprint(f"[CHECK_POINT #{device_host_transfer_counter}: DEVICE ------> HOST] | WRITEBACK | memory_pool_host.py/backup_from_device_all_layer | num_bytes_per_token_per_layer: {num_bytes_per_token_per_layer} bytes | num_bytes_per_token_all_layers: {num_bytes_per_token_all_layers} bytes | num_tokens_per_block: {num_tokens_per_block} | num_bytes_per_block: {num_bytes_per_block} bytes | bytes_transferred: {bytes_transferred} bytes")
        device_host_transfer_counter += 1
    ################################################## CHANGE STRIP ######################################################################

    def get_data_page(self, index, flat: bool = True) -> torch.Tensor:
        if self.layout == "layer_first":
            data_page = self.kv_buffer[:, :, index : index + self.page_size, :, :]
        elif self.layout == "page_first":
            data_page = self.kv_buffer[:, index : index + self.page_size, :, :, :]
        elif self.layout in ["page_first_direct", "page_head"]:
            real_index = index // self.page_size
            data_page = self.kv_buffer[:, real_index : real_index + 1, :, :, :, :]
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        if flat:
            data_page = data_page.flatten()
        return data_page

    def get_dummy_flat_data_page(self) -> torch.Tensor:
        return torch.zeros(
            (2, self.layer_num, self.page_size, self.head_num, self.head_dim),
            dtype=self.dtype,
            device=self.device,
            pin_memory=self.pin_memory,
        ).flatten()

    def set_from_flat_data_page(self, index: int, data_page: torch.Tensor) -> None:
        if self.layout == "layer_first":
            self.kv_buffer[:, :, index : index + self.page_size, :, :] = (
                data_page.reshape(
                    2,
                    self.layer_num,
                    self.page_size,
                    self.head_num,
                    self.head_dim,
                )
            )
        elif self.layout == "page_first":
            self.kv_buffer[:, index : index + self.page_size, :, :, :] = (
                data_page.reshape(
                    2, self.page_size, self.layer_num, self.head_num, self.head_dim
                )
            )
        elif self.layout == "page_first_direct":
            real_index = index // self.page_size
            self.kv_buffer[:, real_index : real_index + 1, :, :, :, :] = (
                data_page.reshape(
                    2, 1, self.layer_num, self.page_size, self.head_num, self.head_dim
                )
            )
        elif self.layout == "page_head":
            real_index = index // self.page_size
            self.kv_buffer[:, real_index : real_index + 1, :, :, :, :] = (
                data_page.reshape(
                    2, 1, self.head_num, self.page_size, self.layer_num, self.head_dim
                )
            )
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")

    def get_page_buffer_meta(self, indices):
        """ "
        meta data for zero copy
        """
        assert len(indices) % self.page_size == 0
        ptr_list = []
        kv_buffer_data_ptr = self.kv_buffer.data_ptr()
        indices = indices.tolist()
        v_offset = (
            self.layer_num
            * self.size
            * self.head_num
            * self.head_dim
            * self.dtype.itemsize
        )
        if self.layout == "layer_first":
            for index in range(0, len(indices), self.page_size):
                for layer_id in range(self.layer_num):
                    k_ptr = (
                        kv_buffer_data_ptr
                        + indices[index]
                        * self.head_num
                        * self.head_dim
                        * self.dtype.itemsize
                        + layer_id
                        * self.size
                        * self.head_num
                        * self.head_dim
                        * self.dtype.itemsize
                    )
                    v_ptr = k_ptr + v_offset
                    ptr_list.append(k_ptr)
                    ptr_list.append(v_ptr)
            element_size = (
                self.dtype.itemsize * self.page_size * self.head_num * self.head_dim
            )
            element_size_list = [element_size] * len(ptr_list)
        elif self.layout in ["page_first", "page_first_direct", "page_head"]:
            for index in range(0, len(indices), self.page_size):
                k_ptr = (
                    kv_buffer_data_ptr
                    + indices[index]
                    * self.layer_num
                    * self.head_num
                    * self.head_dim
                    * self.dtype.itemsize
                )
                v_ptr = k_ptr + v_offset
                ptr_list.append(k_ptr)
                ptr_list.append(v_ptr)
            element_size = (
                self.layer_num
                * self.dtype.itemsize
                * self.page_size
                * self.head_num
                * self.head_dim
            )
            element_size_list = [element_size] * len(ptr_list)
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        return ptr_list, element_size_list


class MLATokenToKVPoolHost(HostKVCache):
    device_pool: MLATokenToKVPool

    def __init__(
        self,
        device_pool: MLATokenToKVPool,
        host_to_device_ratio: float,
        host_size: int,
        page_size: int,
        layout: str,
        pin_memory: bool = True,
        device: str = "cpu",
        allocator_type: str = "default",
    ):
        super().__init__(
            device_pool,
            host_to_device_ratio,
            host_size,
            page_size,
            layout,
            pin_memory,
            device,
            allocator_type,
        )
        self.data_refs = [self.kv_buffer[i] for i in range(self.layer_num)]
        self.data_ptrs = torch.tensor(
            [x.data_ptr() for x in self.data_refs],
            dtype=torch.uint64,
            device=self.device_pool.device,
        )

    def get_size_per_token(self):
        self.kv_lora_rank = self.device_pool.kv_lora_rank
        self.qk_rope_head_dim = self.device_pool.qk_rope_head_dim
        self.layer_num = self.device_pool.layer_num

        return (
            (self.kv_lora_rank + self.qk_rope_head_dim)
            * 1
            * self.dtype.itemsize
            * self.layer_num
        )

    def get_ksize_per_token(self):
        return self.get_size_per_token()

    def init_kv_buffer(self):
        if self.layout == "layer_first":
            dims = (
                self.layer_num,
                self.size,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        elif self.layout == "page_first":
            dims = (
                self.size,
                self.layer_num,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        elif self.layout == "page_first_direct":
            dims = (
                self.page_num,
                self.layer_num,
                self.page_size,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        # Ascend-specific: Aligns with NPUMLATokenToKVPool layout
        # Separately allocate k_buffer and v_buffer for easier data transfer.
        elif self.layout == "page_first_kv_split":
            base_dims = (
                self.page_num,
                self.layer_num,
                self.page_size,
                1,
            )
            alloc_func = ALLOC_MEMORY_FUNCS[self.device_pool.device]
            self.k_buffer = alloc_func(
                (*base_dims, self.kv_lora_rank),
                dtype=self.dtype,
                device=self.device,
                pin_memory=self.pin_memory,
                allocator=self.allocator,
            )
            self.v_buffer = alloc_func(
                (*base_dims, self.qk_rope_head_dim),
                dtype=self.dtype,
                device=self.device,
                pin_memory=self.pin_memory,
                allocator=self.allocator,
            )
            # Return k_buffer to preserve original kv_buffer and data_refs init logic,
            # though Ascend doesn't use these parameters.
            return self.k_buffer
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        self.token_stride_size = (
            self.kv_lora_rank + self.qk_rope_head_dim
        ) * self.dtype.itemsize
        self.layout_dim = self.token_stride_size * self.layer_num

        alloc_func = ALLOC_MEMORY_FUNCS[self.device_pool.device]
        buffer = alloc_func(
            dims,
            dtype=self.dtype,
            device=self.device,
            pin_memory=self.pin_memory,
            allocator=self.allocator,
        )
        return buffer

    def load_to_device_per_layer(
        self, device_pool, host_indices, device_indices, layer_id, io_backend
    ):
        if io_backend == "kernel":
            if self.layout == "layer_first":
                transfer_kv_per_layer_mla(
                    src=self.kv_buffer[layer_id],
                    dst=device_pool.kv_buffer[layer_id],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    item_size=self.token_stride_size,
                )
            elif self.layout == "page_first":
                transfer_kv_per_layer_mla_pf_lf(
                    src=self.kv_buffer,
                    dst=device_pool.kv_buffer[layer_id],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    layer_id=layer_id,
                    item_size=self.token_stride_size,
                    src_layout_dim=self.layout_dim,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "direct":
            if self.layout == "layer_first":
                transfer_kv_direct(
                    src_layers=[self.kv_buffer[layer_id]],
                    dst_layers=[device_pool.kv_buffer[layer_id]],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    page_size=self.page_size,
                )
            elif self.layout == "page_first_direct":
                transfer_kv_per_layer_direct_pf_lf(
                    src_ptrs=[self.kv_buffer],
                    dst_ptrs=[device_pool.kv_buffer[layer_id]],
                    src_indices=host_indices,
                    dst_indices=device_indices,
                    layer_id=layer_id,
                    page_size=self.page_size,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "kernel_ascend":
            if self.layout == "page_first_kv_split":
                # Ascend-specific: transfer KV data for all layers when layer_id == 0
                if layer_id == 0:
                    transfer_kv_dim_exchange(
                        device_indices=device_indices,
                        host_indices=host_indices,
                        device_k=device_pool.k_buffer,
                        host_k=self.k_buffer,
                        device_v=device_pool.v_buffer,
                        host_v=self.v_buffer,
                        page_size=self.page_size,
                        direction=TransferDirection.H2D,
                    )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        else:
            raise ValueError(f"Unsupported IO backend: {io_backend}")

    def backup_from_device_all_layer(
        self, device_pool, host_indices, device_indices, io_backend
    ):
        if io_backend == "kernel":
            if self.layout == "layer_first":
                transfer_kv_all_layer_mla(
                    src_layers=device_pool.data_ptrs,
                    dst_layers=self.data_ptrs,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    item_size=self.token_stride_size,
                    num_layers=self.layer_num,
                )
            elif self.layout == "page_first":
                transfer_kv_all_layer_mla_lf_pf(
                    src_layers=device_pool.data_ptrs,
                    dst=self.kv_buffer,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    item_size=self.token_stride_size,
                    dst_layout_dim=self.layout_dim,
                    num_layers=self.layer_num,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "direct":
            if self.layout == "layer_first":
                transfer_kv_direct(
                    src_layers=device_pool.kv_buffer,
                    dst_layers=self.data_refs,
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    page_size=self.page_size,
                )
            elif self.layout == "page_first_direct":
                transfer_kv_all_layer_direct_lf_pf(
                    src_ptrs=device_pool.kv_buffer,
                    dst_ptrs=[self.kv_buffer],
                    src_indices=device_indices,
                    dst_indices=host_indices,
                    page_size=self.page_size,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        elif io_backend == "kernel_ascend":
            if self.layout == "page_first_kv_split":
                transfer_kv_dim_exchange(
                    device_indices=device_indices,
                    host_indices=host_indices,
                    device_k=device_pool.k_buffer,
                    host_k=self.k_buffer,
                    device_v=device_pool.v_buffer,
                    host_v=self.v_buffer,
                    page_size=self.page_size,
                    direction=TransferDirection.D2H,
                )
            else:
                raise ValueError(f"Unsupported layout: {self.layout}")
        else:
            raise ValueError(f"Unsupported IO backend: {io_backend}")

    def get_data_page(self, index, flat: bool = True) -> torch.Tensor:
        if self.layout == "layer_first":
            data_page = self.kv_buffer[:, index : index + self.page_size, :, :]
        elif self.layout == "page_first":
            data_page = self.kv_buffer[index : index + self.page_size, :, :, :]
        elif self.layout == "page_first_direct":
            real_index = index // self.page_size
            data_page = self.kv_buffer[real_index : real_index + 1, :, :, :, :]
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        if flat:
            data_page = data_page.flatten()
        return data_page

    def get_dummy_flat_data_page(self) -> torch.Tensor:
        return torch.zeros(
            (
                self.layer_num,
                self.page_size,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            ),
            dtype=self.dtype,
            device=self.device,
            pin_memory=self.pin_memory,
        ).flatten()

    def set_from_flat_data_page(self, index: int, data_page: torch.Tensor) -> None:
        if self.layout == "layer_first":
            self.kv_buffer[:, index : index + self.page_size, :, :] = data_page.reshape(
                self.layer_num,
                self.page_size,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        elif self.layout == "page_first":
            self.kv_buffer[index : index + self.page_size, :, :, :] = data_page.reshape(
                self.page_size,
                self.layer_num,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        elif self.layout == "page_first_direct":
            real_index = index // self.page_size
            self.kv_buffer[real_index : real_index + 1, :, :, :, :] = data_page.reshape(
                1,
                self.layer_num,
                self.page_size,
                1,
                self.kv_lora_rank + self.qk_rope_head_dim,
            )
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")

    def get_page_buffer_meta(self, indices):
        """ "
        meta data for zero copy
        """
        assert len(indices) % self.page_size == 0
        ptr_list = []
        kv_buffer_data_ptr = self.kv_buffer.data_ptr()
        indices = indices.tolist()
        if self.layout == "layer_first":
            for index in range(0, len(indices), self.page_size):
                for layer_id in range(self.layer_num):
                    k_ptr = (
                        kv_buffer_data_ptr
                        + indices[index]
                        * (self.kv_lora_rank + self.qk_rope_head_dim)
                        * self.dtype.itemsize
                        + layer_id
                        * self.size
                        * (self.kv_lora_rank + self.qk_rope_head_dim)
                        * self.dtype.itemsize
                    )
                    ptr_list.append(k_ptr)
            element_size = (
                self.dtype.itemsize
                * self.page_size
                * (self.kv_lora_rank + self.qk_rope_head_dim)
            )
            element_size_list = [element_size] * len(ptr_list)
        elif self.layout in ["page_first", "page_first_direct"]:
            for index in range(0, len(indices), self.page_size):
                k_ptr = (
                    kv_buffer_data_ptr
                    + indices[index]
                    * self.layer_num
                    * (self.kv_lora_rank + self.qk_rope_head_dim)
                    * self.dtype.itemsize
                )
                ptr_list.append(k_ptr)
            element_size = (
                self.layer_num
                * self.dtype.itemsize
                * self.page_size
                * (self.kv_lora_rank + self.qk_rope_head_dim)
            )
            element_size_list = [element_size] * len(ptr_list)
        else:
            raise ValueError(f"Unsupported layout: {self.layout}")
        return ptr_list, element_size_list
