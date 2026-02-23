using UnityEngine;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

/// <summary>
/// UDP Receiver for SpellMaster
/// Nhận gesture/combo data từ Python AI Controller
/// </summary>
public class UnityUDPReceiver : MonoBehaviour
{
    [SerializeField] private int port = 5005;
    private UdpClient udpClient;
    private Thread receiveThread;
    private bool isRunning = false;

    // Event để gửi data tới các script khác
    public delegate void GestureEventHandler(string gesture, string combo);
    public static event GestureEventHandler OnGestureDetected;

    // Cache dữ liệu nhận được
    private string lastGesture = "Unknown";
    private string lastCombo = null;

    void Start()
    {
        StartUDPListener();
    }

    void StartUDPListener()
    {
        try
        {
            udpClient = new UdpClient(port);
            isRunning = true;

            // Chạy receive thread
            receiveThread = new Thread(new ThreadStart(ReceiveData));
            receiveThread.IsBackground = true;
            receiveThread.Start();

            Debug.Log($"✓ UDP Listener started on port {port}");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"✗ Error starting UDP listener: {e.Message}");
        }
    }

    void ReceiveData()
    {
        while (isRunning)
        {
            try
            {
                IPEndPoint remoteEndPoint = new IPEndPoint(IPAddress.Any, port);
                byte[] receivedBytes = udpClient.Receive(ref remoteEndPoint);
                string receivedData = Encoding.UTF8.GetString(receivedBytes);

                // Parse JSON
                GestureData data = JsonUtility.FromJson<GestureData>(receivedData);

                lastGesture = data.gesture;
                lastCombo = data.combo;

                Debug.Log($"📥 Received: Gesture={data.gesture}, Combo={data.combo}");

                // Trigger event
                OnGestureDetected?.Invoke(data.gesture, data.combo);
            }
            catch (System.Exception e)
            {
                if (isRunning) // Ignore exception khi đóng
                {
                    Debug.LogWarning($"UDP Receive Error: {e.Message}");
                }
            }
        }
    }

    /// <summary>
    /// Lấy gesture gần nhất
    /// </summary>
    public string GetLastGesture()
    {
        return lastGesture;
    }

    /// <summary>
    /// Lấy combo gần nhất
    /// </summary>
    public string GetLastCombo()
    {
        return lastCombo;
    }

    void OnDestroy()
    {
        StopUDPListener();
    }

    void StopUDPListener()
    {
        isRunning = false;
        if (receiveThread != null)
        {
            receiveThread.Join();
        }
        if (udpClient != null)
        {
            udpClient.Close();
        }
        Debug.Log("✓ UDP Listener stopped");
    }

    /// <summary>
    /// JSON Data Structure - phải match với Python
    /// </summary>
    [System.Serializable]
    public class GestureData
    {
        public string gesture;
        public string combo;
        public long timestamp;
    }
}

/// <summary>
/// Example: Spell Caster - sử dụng gesture để cast spell
/// </summary>
public class SpellCaster : MonoBehaviour
{
    void Start()
    {
        // Subscribe vào event
        UnityUDPReceiver.OnGestureDetected += HandleGesture;
    }

    void HandleGesture(string gesture, string combo)
    {
        if (combo != null)
        {
            // Combo detected
            HandleCombo(combo);
        }
        else
        {
            // Single gesture
            HandleSingleGesture(gesture);
        }
    }

    void HandleSingleGesture(string gesture)
    {
        Debug.Log($"🎯 Gesture: {gesture}");

        switch (gesture)
        {
            case "Open":
                CastSpell("OpenHand");
                break;
            case "Fist":
                CastSpell("Fist");
                break;
            case "ThumbsUp":
                CastSpell("ThumbsUp");
                break;
            case "Peace":
                CastSpell("Peace");
                break;
            case "OK":
                CastSpell("OK");
                break;
        }
    }

    void HandleCombo(string combo)
    {
        Debug.Log($"⚡ Combo: {combo}");

        switch (combo)
        {
            case "Spell_Peace+Peace":
                CastSpell("FireStrike");
                break;
            case "Spell_ThumbsUp+ThumbsUp":
                CastSpell("HealingLight");
                break;
            case "Spell_Fist+Open":
                CastSpell("PowerShield");
                break;
        }
    }

    void CastSpell(string spellName)
    {
        Debug.Log($"✨ Casting spell: {spellName}");
        // TODO: Add animation, effects, logic...
    }

    void OnDestroy()
    {
        UnityUDPReceiver.OnGestureDetected -= HandleGesture;
    }
}
