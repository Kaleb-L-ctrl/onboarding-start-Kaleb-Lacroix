module SPI_peripheral #(
    parameter SYNC_FLOPS = 2
)
(
    input wire       SCLK,// clock
    input wire       COPI,//in from controller
    input wire       nCS,//start transaction on negedge
    input wire       clk,//
    input wire       rst_n,// 

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8, 
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

reg [4:0] curr_bit; 
reg [15:0] transaction_data;

reg [SYNC_FLOPS-1:0] SCLK_sync;
reg [SYNC_FLOPS-1:0] COPI_sync;
reg [SYNC_FLOPS-1:0] nCS_sync;

always @(posedge clk or negedge rst_n) begin

    if (!rst_n) begin //reset state
        curr_bit <= 5'b0;
        transaction_data <= 16'b0;

        SCLK_sync <= 0;
        COPI_sync <= 0;
        nCS_sync <= 0;

        en_reg_out_7_0 <= 8'b0;
        en_reg_out_15_8 <= 8'b0;
        en_reg_pwm_7_0 <= 8'b0;
        en_reg_pwm_15_8 <= 8'b0;
        pwm_duty_cycle <= 8'b0;
    end else begin
        //capture on clock cycle
        SCLK_sync <= {SCLK_sync[SYNC_FLOPS-2:0], SCLK};
        COPI_sync <= {COPI_sync[SYNC_FLOPS-2:0], COPI};  // Use COPI_sync
        nCS_sync <= {nCS_sync[SYNC_FLOPS-2:0], nCS};     // Use nCS_sync
        
        if(nCS_sync == 2'b10) begin //negedge. begin data capture
            curr_bit <= 5'b0;
            transaction_data <= 16'b0;
        end

        else if (nCS_sync == 2'b00 && SCLK_sync == 2'b01) begin //posedge detect SCLK when data is valid
            if (curr_bit!=5'b10000) begin
                    transaction_data[15 - curr_bit] <= COPI_sync[SYNC_FLOPS-1];
                    curr_bit <= curr_bit + 1;
                end
        end
        if(curr_bit[4] == 1'b1 && transaction_data[15] == 1'b1) begin
            case (transaction_data[14:8]) 
                7'b0000000: en_reg_out_7_0 <= transaction_data[7:0];
                7'b0000001: en_reg_out_15_8 <= transaction_data[7:0];
                7'b0000010: en_reg_pwm_7_0 <= transaction_data[7:0];
                7'b0000011: en_reg_pwm_15_8 <= transaction_data[7:0];
                7'b0000100: pwm_duty_cycle <= transaction_data[7:0];
                default: ;
            endcase
        end
    end
end


endmodule