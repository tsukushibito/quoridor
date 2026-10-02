import ctypes as C
import json,os,sys,hashlib,urllib.request,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'.artifacts/ai-sigma/resume-20261002/WEBGPU-MEASURE/environment-inspection.json'
r={'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'NN':0,'device_files':{p:Path(p).exists() for p in ['/dev/dxg','/dev/dri','/dev/nvidia0']},'driver_capabilities':os.environ.get('NVIDIA_DRIVER_CAPABILITIES'),'LIBGL_ALWAYS_SOFTWARE_parent':os.environ.get('LIBGL_ALWAYS_SOFTWARE'),'ICD_files':{p:list(map(str,Path(p).glob('*.json'))) for p in ['/etc/vulkan/icd.d','/usr/share/vulkan/icd.d']}}
class Application(C.Structure):
 _fields_=[('sType',C.c_uint32),('pNext',C.c_void_p),('pApplicationName',C.c_char_p),('applicationVersion',C.c_uint32),('pEngineName',C.c_char_p),('engineVersion',C.c_uint32),('apiVersion',C.c_uint32)]
class Instance(C.Structure):
 _fields_=[('sType',C.c_uint32),('pNext',C.c_void_p),('flags',C.c_uint32),('pApplicationInfo',C.POINTER(Application)),('enabledLayerCount',C.c_uint32),('ppEnabledLayerNames',C.c_void_p),('enabledExtensionCount',C.c_uint32),('ppEnabledExtensionNames',C.c_void_p)]
try:
 vk=C.CDLL('libvulkan.so.1');app=Application(0,None,b'sigma115-readonly',1,None,0,1<<22);ci=Instance(1,None,0,C.pointer(app),0,None,0,None);handle=C.c_void_p();vk.vkCreateInstance.argtypes=[C.POINTER(Instance),C.c_void_p,C.POINTER(C.c_void_p)];vk.vkCreateInstance.restype=C.c_int32
 code=vk.vkCreateInstance(C.byref(ci),None,C.byref(handle));r['native_Vulkan']={'vkCreateInstance':code,'VK_ERROR_INCOMPATIBLE_DRIVER':-9,'physical_device_count':None}
 if code==0:
  count=C.c_uint32();vk.vkEnumeratePhysicalDevices.argtypes=[C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p];rc=vk.vkEnumeratePhysicalDevices(handle,C.byref(count),None);r['native_Vulkan'].update(enumerate_code=rc,physical_device_count=count.value);vk.vkDestroyInstance.argtypes=[C.c_void_p,C.c_void_p];vk.vkDestroyInstance(handle,None);r['native_Vulkan']['instance_destroyed']=True
except Exception as error:r['native_Vulkan']={'error':str(error)}
package=ROOT/'.artifacts/ai-sigma/reference/SIGMA-WEB-REFERENCE/ort-package.json';local=json.loads(package.read_text());r['local_ORT']={'version':local['version'],'package_SHA256':hashlib.sha256(package.read_bytes()).hexdigest(),'webgpu_export':local['exports']['./webgpu'],'existing_assets':sorted(p.name for p in package.parent.glob('ort*'))}
url='https://registry.npmjs.org/onnxruntime-web/1.21.0'
try:
 with urllib.request.urlopen(url,timeout=10) as response:body=response.read(200000)
 metadata=json.loads(body);assert metadata['version']==local['version']=='1.21.0'
 r['official_exact_version_metadata']={'url':url,'version':metadata['version'],'metadata_bytes':len(body),'metadata_SHA256':hashlib.sha256(body).hexdigest(),'dist':metadata['dist'],'requested_webgpu_bundle':'dist/ort.webgpu.min.js','additional_jsep_wasm_mjs_already_local':True,'asset_downloaded':False,'reason':'Physical WebGPU precondition currently absent; no model dispatch or measurement started.'}
except Exception as error:r['official_exact_version_metadata']={'url':url,'error':str(error)}
out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
