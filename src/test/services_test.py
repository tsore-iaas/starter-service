import grpc
import vm_pb2
import vm_pb2_grpc

def test_services():
    # Connexion au service VMConfig
    with grpc.insecure_channel('localhost:50051') as channel:
        vm_client = vm_pb2_grpc.VMConfigStub(channel)
        response = vm_client.SaveTemplate(
            vm_pb2.TemplateRequest(name="ubuntu", config="config-data")
        )
        print("VMConfig Response:", response.message)

    # Connexion au service LoadBalancer
    with grpc.insecure_channel('localhost:50052') as channel:
        lb_client = vm_pb2_grpc.LoadBalancerStub(channel)
        response = lb_client.AllocateVM(
            vm_pb2.VMRequest(template_name="ubuntu", machine_id="machine1")
        )
        print("LoadBalancer Response:", response.message)

if __name__ == "__main__":
    test_services()
