package org.healthchallenge.hidvia;

import android.Manifest;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanFilter;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.os.ParcelUuid;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.UUID;

import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.content.ContentValues;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.view.Window;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.json.JSONObject;

/** Lightweight Android shell for the bundled offline patient demo.
 * NOT certified as a medical device; not designed for real patient records.
 */
public final class MainActivity extends Activity implements SensorEventListener {
    private static final int PICK_IMAGE = 90;
    private static final int NOTIFICATION_PERMISSION = 91;
    private static final String LOCAL = "file:///android_asset/patient.html";
    private static final String CHANNEL = "hidvia-demo-updates";
    private WebView web;
    private ValueCallback<Uri[]> fileCallback;
    private Uri cameraUri;
    private SensorManager sensors;
    private final Map<String, Float> sensorValues = new ConcurrentHashMap<>();
    private String clinicOrigin = "";
    private static final int RNA_BT_PERMISSION = 94;
    private BluetoothLeScanner rnaScanner;
    private ScanCallback rnaScanCallback;
    private BluetoothGatt rnaGatt;
    private UUID rnaService, rnaCharacteristic;
    private final android.os.Handler rnaTimeout=new android.os.Handler(android.os.Looper.getMainLooper());
    private void rnaStatus(String message){
        runOnUiThread(()->{
            String js="var x=document.getElementById('rnaStatus');if(x)x.textContent="+JSONObject.quote(message)+";";
            web.evaluateJavascript(js,null);
        });
    }
    private void deliverRna(byte[] bytes){
        if(bytes==null || bytes.length==0 || bytes.length>4096){rnaStatus("Invalid BLE frame length");return;}
        String raw=new String(bytes,StandardCharsets.UTF_8);
        try{JSONObject parsed=new JSONObject(raw);if(!"hidvia-rna-v1".equals(parsed.optString("schema")))throw new Exception("schema");}
        catch(Exception e){rnaStatus("Vendor device does not emit compatible single-frame JSON; an adapter is required.");return;}
        runOnUiThread(()->web.evaluateJavascript("window.HidviaRnaReceive("+JSONObject.quote(raw)+");",null));
    }
    private void stopRnaScan(){
        if(rnaScanner!=null && rnaScanCallback!=null){
            try{rnaScanner.stopScan(rnaScanCallback);}catch(SecurityException ignored){}
            rnaScanCallback=null;
        }
    }
    private void connectRna(String service, String characteristic){
        try{rnaService=UUID.fromString(service);rnaCharacteristic=UUID.fromString(characteristic);}
        catch(Exception ex){rnaStatus("Enter valid vendor 128-bit service and characteristic UUIDs.");return;}
        if(Build.VERSION.SDK_INT>=31 && (checkSelfPermission(Manifest.permission.BLUETOOTH_SCAN)!=PackageManager.PERMISSION_GRANTED || checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED)){
            requestPermissions(new String[]{Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT},RNA_BT_PERMISSION);
            rnaStatus("Grant Bluetooth permissions and tap Connect BLE again.");return;
        }
        if(Build.VERSION.SDK_INT<31 && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION},RNA_BT_PERMISSION);
            rnaStatus("Grant Bluetooth scan location permission and tap Connect BLE again.");return;
        }
        BluetoothManager manager=(BluetoothManager)getSystemService(BLUETOOTH_SERVICE);
        BluetoothAdapter adapter=manager==null?null:manager.getAdapter();
        if(adapter==null||!adapter.isEnabled()){rnaStatus("Enable Bluetooth in Android settings.");return;}
        stopRnaScan();if(rnaGatt!=null){rnaGatt.close();rnaGatt=null;}
        rnaScanner=adapter.getBluetoothLeScanner();if(rnaScanner==null){rnaStatus("Bluetooth LE scanning unavailable.");return;}
        rnaScanCallback=new ScanCallback(){
            @Override public void onScanResult(int callbackType,ScanResult result){
                stopRnaScan();rnaStatus("BLE device discovered; connecting...");
                BluetoothDevice device=result.getDevice();
                try{rnaGatt=device.connectGatt(MainActivity.this,false,new BluetoothGattCallback(){
                    @Override public void onConnectionStateChange(BluetoothGatt g,int status,int state){
                        if(status!=BluetoothGatt.GATT_SUCCESS||state==BluetoothProfile.STATE_DISCONNECTED){rnaStatus("BLE disconnected ("+status+").");g.close();return;}
                        if(state==BluetoothProfile.STATE_CONNECTED){rnaStatus("BLE connected; discovering service...");try{g.discoverServices();}catch(SecurityException ignored){rnaStatus("Bluetooth permission denied");}}
                    }
                    @Override public void onServicesDiscovered(BluetoothGatt g,int status){
                        if(status!=BluetoothGatt.GATT_SUCCESS){rnaStatus("Could not discover RNA service");return;}
                        BluetoothGattService svc=g.getService(rnaService);
                        BluetoothGattCharacteristic c=svc==null?null:svc.getCharacteristic(rnaCharacteristic);
                        if(c==null){rnaStatus("Configured vendor characteristic not found");return;}
                        if((c.getProperties()&BluetoothGattCharacteristic.PROPERTY_NOTIFY)!=0){
                            try{g.setCharacteristicNotification(c,true);
                                BluetoothGattDescriptor descriptor=c.getDescriptor(UUID.fromString("00002902-0000-1000-8000-00805f9b34fb"));
                                if(descriptor!=null){descriptor.setValue(BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE);g.writeDescriptor(descriptor);}
                                rnaStatus("BLE notifications enabled; waiting for research JSON frame.");}
                            catch(SecurityException ex){rnaStatus("BLE permission denied");}
                        }else if((c.getProperties()&BluetoothGattCharacteristic.PROPERTY_READ)!=0){
                            try{g.readCharacteristic(c);}catch(SecurityException ex){rnaStatus("BLE permission denied");}
                        }else rnaStatus("Characteristic is neither readable nor notifiable.");
                    }
                    @Override public void onCharacteristicRead(BluetoothGatt g,BluetoothGattCharacteristic c,int status){if(status==BluetoothGatt.GATT_SUCCESS)deliverRna(c.getValue());}
                    @Override public void onCharacteristicChanged(BluetoothGatt g,BluetoothGattCharacteristic c){deliverRna(c.getValue());}
                });}catch(SecurityException ex){rnaStatus("Bluetooth permission denied");}
            }
            @Override public void onScanFailed(int errorCode){rnaStatus("BLE scan failed: "+errorCode);}
        };
        ScanFilter filter=new ScanFilter.Builder().setServiceUuid(new ParcelUuid(rnaService)).build();
        try{rnaScanner.startScan(Arrays.asList(filter),new ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(),rnaScanCallback);
            rnaStatus("Scanning for vendor RNA BLE service (up to 15 seconds)...");
            rnaTimeout.postDelayed(()->{if(rnaScanCallback!=null){stopRnaScan();rnaStatus("BLE scan timed out; verify UUID and device advertising.");}},15000);
        }catch(SecurityException ex){rnaStatus("Bluetooth scan permission denied");}
    }


    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        getWindow().setStatusBarColor(Color.rgb(230,245,242));
        getWindow().setNavigationBarColor(Color.WHITE);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR | View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        clinicOrigin = getPreferences(MODE_PRIVATE).getString("clinicOrigin", "");
        web = new WebView(this);
        web.setBackgroundColor(Color.rgb(244,248,248));
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        // Apply BOTH system bar insets. Content and the bottom tabs never overlap gesture/navigation bars.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            getWindow().setDecorFitsSystemWindows(false);
            web.setOnApplyWindowInsetsListener((view,insets)->{
                android.graphics.Insets sys = insets.getInsets(
                    WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars() | WindowInsets.Type.displayCutout());
                view.setPadding(sys.left,sys.top,sys.right,sys.bottom);
                return insets;
            });
        } else {
            web.setFitsSystemWindows(true);
        }
        setContentView(web);
        WebSettings ws=web.getSettings();
        ws.setJavaScriptEnabled(true);ws.setDomStorageEnabled(true);
        ws.setAllowFileAccess(true);ws.setAllowContentAccess(true);
        ws.setAllowFileAccessFromFileURLs(false);ws.setAllowUniversalAccessFromFileURLs(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        ws.setSupportZoom(false);
        if (Build.VERSION.SDK_INT>=26)ws.setSafeBrowsingEnabled(true);
        web.addJavascriptInterface(new NativeBridge(),"HidviaNative");
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request){
                Uri url=request.getUrl();
                String str=url.toString();
                if (str.startsWith("file:///android_asset/") || (!clinicOrigin.isEmpty() && str.startsWith(clinicOrigin+"/")))return false;
                try{startActivity(new Intent(Intent.ACTION_VIEW,url));}catch(Exception ignored){}
                return true;
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error){
                if(request.isForMainFrame() && (view.getUrl()==null || !view.getUrl().startsWith("file:///android_asset/")))view.loadUrl(LOCAL);
            }
        });
        web.setWebChromeClient(new WebChromeClient(){
            @Override public boolean onShowFileChooser(WebView w,ValueCallback<Uri[]> callback,FileChooserParams params){
                if(fileCallback!=null)fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent gallery=new Intent(Intent.ACTION_GET_CONTENT);String accept=(params.getAcceptTypes()!=null && params.getAcceptTypes().length>0)?params.getAcceptTypes()[0]:"image/*";
                boolean rnaImport=accept.contains("json")||accept.contains(".json");
                gallery.setType(rnaImport?"application/json":"image/*");gallery.addCategory(Intent.CATEGORY_OPENABLE);
                Intent camera=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                Intent[] extra=new Intent[0];
                if(!rnaImport && camera.resolveActivity(getPackageManager())!=null){
                    ContentValues values=new ContentValues();values.put(MediaStore.Images.Media.TITLE,"HIDVIA demo image");
                    values.put(MediaStore.Images.Media.MIME_TYPE,"image/jpeg");
                    cameraUri=getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI,values);
                    if(cameraUri!=null){camera.putExtra(MediaStore.EXTRA_OUTPUT,cameraUri);camera.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);extra=new Intent[]{camera};}
                }
                Intent chooser=Intent.createChooser(gallery,rnaImport?"Select research RNA JSON":"Select a demo image");chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS,extra);
                try{startActivityForResult(chooser,PICK_IMAGE);}catch(ActivityNotFoundException ex){callback.onReceiveValue(null);fileCallback=null;return false;}
                return true;
            }
            @Override public void onPermissionRequest(PermissionRequest request){request.deny();}
        });
        sensors=(SensorManager)getSystemService(SENSOR_SERVICE);
        NotificationManager mgr=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        mgr.createNotificationChannel(new NotificationChannel(CHANNEL,"HIDVIA demo updates",NotificationManager.IMPORTANCE_DEFAULT));
        if(!clinicOrigin.isEmpty())web.loadUrl(clinicOrigin+"/patient"); else web.loadUrl(LOCAL);
    }

    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(request!=PICK_IMAGE||fileCallback==null)return;
        Uri[] files=null;
        if(result==RESULT_OK){
            if(data!=null && data.getData()!=null)files=new Uri[]{data.getData()};
            else if(cameraUri!=null)files=new Uri[]{cameraUri};
        }
        fileCallback.onReceiveValue(files);fileCallback=null;cameraUri=null;
    }
    @Override protected void onResume(){super.onResume();if(sensors!=null){
        int[] types={Sensor.TYPE_ACCELEROMETER,Sensor.TYPE_GYROSCOPE,Sensor.TYPE_LIGHT,Sensor.TYPE_PRESSURE,Sensor.TYPE_PROXIMITY};
        for(int type:types){Sensor sensor=sensors.getDefaultSensor(type);if(sensor!=null)sensors.registerListener(this,sensor,SensorManager.SENSOR_DELAY_NORMAL);}
        if(Build.VERSION.SDK_INT<29||checkSelfPermission(Manifest.permission.ACTIVITY_RECOGNITION)==PackageManager.PERMISSION_GRANTED){Sensor steps=sensors.getDefaultSensor(Sensor.TYPE_STEP_COUNTER);if(steps!=null)sensors.registerListener(this,steps,SensorManager.SENSOR_DELAY_NORMAL);}
        if(checkSelfPermission(Manifest.permission.BODY_SENSORS)==PackageManager.PERMISSION_GRANTED){Sensor pulse=sensors.getDefaultSensor(Sensor.TYPE_HEART_RATE);if(pulse!=null)sensors.registerListener(this,pulse,SensorManager.SENSOR_DELAY_NORMAL);}
    }}
    @Override protected void onPause(){if(sensors!=null)sensors.unregisterListener(this);super.onPause();}
    @Override public void onSensorChanged(SensorEvent e){
        String name;float value=e.values[0];
        switch(e.sensor.getType()){
            case Sensor.TYPE_ACCELEROMETER:name="acceleration_m_s2";value=(float)Math.sqrt(e.values[0]*e.values[0]+e.values[1]*e.values[1]+e.values[2]*e.values[2]);break;
            case Sensor.TYPE_GYROSCOPE:name="gyro_rad_s";value=(float)Math.sqrt(e.values[0]*e.values[0]+e.values[1]*e.values[1]+e.values[2]*e.values[2]);break;
            case Sensor.TYPE_LIGHT:name="ambient_light_lux";break;
            case Sensor.TYPE_PRESSURE:name="ambient_pressure_hpa";break;
            case Sensor.TYPE_PROXIMITY:name="proximity_cm";break;
            case Sensor.TYPE_STEP_COUNTER:name="steps_since_boot";break;
            case Sensor.TYPE_HEART_RATE:name="heart_rate_bpm";break;
            default:return;
        }
        sensorValues.put(name,value);
    }
    @Override public void onAccuracyChanged(Sensor sensor,int accuracy){}
    @Override public void onBackPressed(){if(web.canGoBack())web.goBack();else super.onBackPressed();}
    @Override public void onDestroy(){stopRnaScan();if(rnaGatt!=null)rnaGatt.close();if(web!=null){web.removeJavascriptInterface("HidviaNative");web.destroy();}super.onDestroy();}

    public class NativeBridge {
        @JavascriptInterface public void connectRnaBle(String serviceUUID,String charUUID){
            runOnUiThread(()->connectRna(serviceUUID,charUUID));
        }

        @JavascriptInterface public String getSensors(){
            JSONObject json=new JSONObject();
            try{for(Map.Entry<String,Float> entry:sensorValues.entrySet())json.put(entry.getKey(),entry.getValue());
                json.put("researchOnly",true);json.put("stepsCounterIsSinceBoot",true);
                json.put("permissionHint","Activity Recognition and Body Sensors are optional Android permissions; unavailable signals are omitted.");
            }catch(Exception ignored){}
            return json.toString(2);
        }
        @JavascriptInterface public void openClinic(String raw){
            runOnUiThread(()->{
                try{
                    Uri u=Uri.parse(raw);String host=u.getHost();String scheme=u.getScheme();
                    if(host==null||(!"https".equals(scheme)&&!"http".equals(scheme)))return;
                    // Plain HTTP is demo-only: limit to emulator or RFC1918 addresses.
                    if("http".equals(scheme)&&!host.equals("10.0.2.2")&&!host.equals("localhost")&&!host.matches("192\\.168\\.\\d{1,3}\\.\\d{1,3}")&&!host.matches("10\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}"))return;
                    clinicOrigin=u.getScheme()+"://"+u.getAuthority();
                    getPreferences(MODE_PRIVATE).edit().putString("clinicOrigin",clinicOrigin).apply();
                    web.loadUrl(clinicOrigin+"/patient");
                }catch(Exception ignored){}
            });
        }
        @JavascriptInterface public void notifyLocal(String title,String body){
            runOnUiThread(()->{
                if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
                    requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFICATION_PERMISSION);return;
                }
                android.app.Notification n=new android.app.Notification.Builder(MainActivity.this,CHANNEL)
                    .setContentTitle(title).setContentText(body).setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setAutoCancel(true).build();
                NotificationManager m=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
                m.notify((int)(System.currentTimeMillis()%100000),n);
            });
        }
        @JavascriptInterface public void requestActivitySensorPermissions(){
            runOnUiThread(()->requestPermissions(new String[]{Manifest.permission.ACTIVITY_RECOGNITION,Manifest.permission.BODY_SENSORS},93));
        }
    }
}
