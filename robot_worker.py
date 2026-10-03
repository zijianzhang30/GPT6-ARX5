"""Isolated vendor controller process. Construction may HOME the arm.
Only launched by the explicit live-connect action in the web interface.
"""
import os,sys,json,time,threading,queue,socket,struct
from pathlib import Path
arm=None
out=os.fdopen(os.dup(1),'w',buffering=1)
os.dup2(2,1)  # vendor C++ output belongs in the log, not the JSON stream

def emit(value):
    out.write(json.dumps(value,allow_nan=False)+'\n');out.flush()

def main():
    global arm
    root=Path(__file__).resolve().parent
    channel=sys.argv[1]
    commands=queue.Queue();rx={'last':0.,'count':0,'ids':set()}
    bus=socket.socket(socket.PF_CAN,socket.SOCK_RAW,socket.CAN_RAW)
    bus.bind((channel,));bus.settimeout(.2)
    def monitor():
        while True:
            try:
                data,anc,flags,addr=bus.recvmsg(16)
                if flags & socket.MSG_DONTROUTE:continue  # local transmit echo is not robot feedback
                canid,length,payload=struct.unpack('=IB3x8s',data)
                if canid & 0x20000000:continue
                rx['last']=time.monotonic();rx['count']+=1;rx['ids'].add(canid)
            except socket.timeout:continue
            except OSError:return
    threading.Thread(target=monitor,daemon=True).start()
    def reader():
        for line in sys.stdin:
            try:commands.put(json.loads(line))
            except ValueError:pass
        commands.put({'action':'shutdown'})
    threading.Thread(target=reader,daemon=True).start()
    emit({'status':'initializing','message':'SDK 正在初始化电机/回零，请保持工作区空旷'})
    sys.path.insert(0,str(root/'native_live/build'))
    import r5_live_sdk as arx
    arm=arx.InterfacesPy(str(root/'vendor/R5-master/py/ARX_R5_python/bimanual/script/X5liteaa0.urdf'),channel,0)
    arm.arx_x(500,2000,10)
    # Start in vendor PROTECT mode after its initialization, not an invented zero target.
    arm.set_arm_status(2)
    from worker_control import PROTOCOL_VERSION, WorkerControl
    control=WorkerControl(arm)
    emit({'status':'ready'})
    while True:
        batch=[]
        for _ in range(64):
            try:batch.append(commands.get_nowait())
            except queue.Empty:break
        age=max(0.,time.monotonic()-rx['last'])
        errors=list(arm.get_error_codes())
        control.cycle(batch,rx_age=age,error_codes=errors)
        if control.closed:
            emit({'status':'closed'});time.sleep(.05);os._exit(0)
        q=list(arm.get_joint_positions());vel=list(arm.get_joint_velocities());curr=list(arm.get_joint_currents())
        emit({'status':'feedback','sample_time':time.monotonic(),'q':q,'velocity':vel,'current':curr,'rx_age':max(0.,time.monotonic()-rx['last']),'rx_count':rx['count'],'rx_ids':sorted(rx['ids']),'active':control.active,'fault':control.fault is not None,'fault_reason':control.fault,'worker_protocol_version':PROTOCOL_VERSION,'error_codes':errors})
        time.sleep(.02)

if __name__=='__main__':
    try:main()
    except BaseException as e:
        if arm is not None:
            try:arm.set_arm_status(2);time.sleep(.05)
            except Exception:pass
        emit({'status':'error','message':str(e)})
        raise
